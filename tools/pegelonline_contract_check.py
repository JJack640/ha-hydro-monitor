"""Check that the live PEGELONLINE API still looks the way Hydro Monitor expects.

The PEGELONLINE REST API v2 is documented and stable, but the service is
also moving to a new HyDAS API, and units and status words are data, not
schema. This on-demand check fetches the station list and the data of one
reference gauge (Kaub, water level and discharge) and verifies what the
provider relies on:

    python -m tools.pegelonline_contract_check

Exit code 0: everything is as expected. Exit code 1: drift was found (every
problem is listed). It makes a handful of read-only requests (the station
list is about 60 KB compressed).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from typing import Any

from aiohttp import ClientSession

from custom_components.hydro_monitor.providers.pegelonline.api import (
    PegelonlineClient,
    PegelonlineError,
)

REFERENCE_STATION = "KAUB"

# The words the service documents for `stateMnwMhw` (low, normal, high,
# unknown, commented, out-dated). Anything else is reported so it can be
# handled on purpose.
KNOWN_STATES = frozenset(
    {"low", "normal", "high", "unknown", "commented", "out-dated"}
)

# What the trend code understands: the unit's length part, before any datum
# ("m+NN", "m+PNP", "m. ü. NN" are metres).
_LENGTH_UNITS = frozenset({"m", "cm", "mm"})
_DISCHARGE_UNIT = "m³/s"

_REQUIRED_STATION_KEYS = ("uuid", "longname", "timeseries")


def _length_unit(unit: str) -> str:
    return unit.split()[0].split("+")[0].rstrip(".")


def check_station_list(
    stations: Any,
    *,
    minimum_water_level: int = 500,
    minimum_discharge: int = 50,
) -> list[str]:
    """Return the problems with the station list (with time series)."""
    if not isinstance(stations, list) or not stations:
        return ["stations: response is not a non-empty list"]

    problems: list[str] = []
    water_level = discharge = 0
    bad_units: set[str] = set()
    missing_keys: set[str] = set()
    without_interval = 0

    for station in stations:
        if not isinstance(station, dict):
            problems.append(f"stations: entry is not an object: {station!r}")
            continue

        missing_keys.update(k for k in _REQUIRED_STATION_KEYS if k not in station)

        for series in station.get("timeseries") or []:
            if not isinstance(series, dict):
                continue

            name = series.get("shortname")
            unit = series.get("unit")

            if name == "W":
                water_level += 1
                if not isinstance(unit, str) or _length_unit(unit) not in _LENGTH_UNITS:
                    bad_units.add(f"W/{unit!r}")
            elif name == "Q":
                discharge += 1
                if unit != _DISCHARGE_UNIT:
                    bad_units.add(f"Q/{unit!r}")
            else:
                continue

            if not isinstance(series.get("equidistance"), int):
                without_interval += 1

    if missing_keys:
        problems.append(f"stations: missing key(s) {sorted(missing_keys)}")
    if bad_units:
        problems.append(f"stations: unexpected unit(s) {sorted(bad_units)}")
    if without_interval:
        problems.append(f"stations: {without_interval} series without an interval")
    if water_level < minimum_water_level:
        problems.append(
            f"stations: only {water_level} water-level series "
            f"(expected at least {minimum_water_level})"
        )
    if discharge < minimum_discharge:
        problems.append(
            f"stations: only {discharge} discharge series "
            f"(expected at least {minimum_discharge})"
        )

    return problems


def check_measurements(label: str, points: Any) -> list[str]:
    """Return the problems with one list of raw measurements."""
    if not isinstance(points, list) or not points:
        return [f"{label}: measurements are not a non-empty list"]

    for point in points:
        if not isinstance(point, dict):
            return [f"{label}: measurement is not an object: {point!r}"]

        timestamp = point.get("timestamp")
        try:
            parsed = datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            return [f"{label}: unreadable timestamp {timestamp!r}"]

        if parsed.tzinfo is None:
            return [f"{label}: timestamp without an offset: {timestamp!r}"]

        value = point.get("value")
        if not isinstance(value, int | float) or isinstance(value, bool):
            return [f"{label}: non-numeric value {value!r}"]

    return []


def check_timeseries(label: str, data: Any, *, water_level: bool) -> list[str]:
    """Return the problems with one time series incl. current measurement."""
    if not isinstance(data, dict):
        return [f"{label}: time series is not an object"]

    problems: list[str] = []
    unit = data.get("unit")

    if not isinstance(unit, str):
        problems.append(f"{label}: no unit")
    elif water_level and _length_unit(unit) not in _LENGTH_UNITS:
        problems.append(f"{label}: unexpected water level unit {unit!r}")
    elif not water_level and unit != _DISCHARGE_UNIT:
        problems.append(f"{label}: unexpected discharge unit {unit!r}")

    current = data.get("currentMeasurement")
    if not isinstance(current, dict):
        return [*problems, f"{label}: no currentMeasurement"]

    if water_level:
        state = current.get("stateMnwMhw")
        if state not in KNOWN_STATES:
            problems.append(f"{label}: unknown stateMnwMhw {state!r}")

    return problems


async def _check_live() -> list[str]:
    """Run every check against the live PEGELONLINE API."""
    async with ClientSession() as session:
        client = PegelonlineClient(session)
        problems: list[str] = []

        try:
            stations = await client.async_get_stations()
        except PegelonlineError as err:
            return [f"station list request failed: {err}"]

        problems.extend(check_station_list(stations))

        reference = next(
            (s for s in stations if s.get("shortname") == REFERENCE_STATION), None
        )
        if reference is None:
            problems.append(f"reference station {REFERENCE_STATION} is missing")
            return problems

        for series in ("W", "Q"):
            label = f"{REFERENCE_STATION}/{series}"

            try:
                problems.extend(
                    check_measurements(
                        label,
                        await client.async_get_measurements(reference["uuid"], series),
                    )
                )
                problems.extend(
                    check_timeseries(
                        label,
                        await client.async_get_timeseries(reference["uuid"], series),
                        water_level=series == "W",
                    )
                )
            except PegelonlineError as err:
                problems.append(f"{label} request failed: {err}")

        return problems


def main() -> int:
    """Run the check and print a report; return the process exit code."""
    problems = asyncio.run(_check_live())

    if not problems:
        print(
            "OK: the PEGELONLINE station list, units and the reference gauge "
            f"({REFERENCE_STATION}) match what Hydro Monitor expects."
        )
        return 0

    print(f"PEGELONLINE API drift detected ({len(problems)} problem(s)):")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

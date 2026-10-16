"""Check that the live NIWIS API still offers everything Hydro Monitor requests.

NIWIS publishes no OpenAPI description and no changelog, and in 2026-10 it
silently restructured its derived-quantity catalogue (quantities renamed,
moved to other endpoints or removed outright), which broke several sensors
until someone noticed. This on-demand check compares what the integration
asks for (derived from providers/niwis/const.py) with what NIWIS currently
offers, and probes the map-classification endpoint that now provides the
current low-water class:

    python -m tools.niwis_contract_check

Exit code 0: everything the integration needs is still there. Exit code 1:
drift was found (every problem is listed). It makes a handful of read-only
requests (the catalogue plus one ~100 KB classification list per
measurement type).
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterable
from typing import Any

from aiohttp import ClientSession

from custom_components.hydro_monitor.providers.niwis import const as niwis_const
from custom_components.hydro_monitor.providers.niwis.api import (
    NiwisClient,
    NiwisError,
)

# The class vocabulary the integration knows how to map (plus NIWIS's own
# "no data" marker). Anything else is reported so it can be mapped on purpose.
KNOWN_KARTE_CLASSES = frozenset(
    {
        "EXTREM_NIEDRIG",
        "SEHR_NIEDRIG",
        "NIEDRIG",
        "KEIN_NIEDRIGWASSER",
        "KEINE_DATEN",
    }
)


def expected_quantities() -> list[tuple[str, str]]:
    """Return the (endpoint, abgeleiteteGroesse) pairs the integration requests."""
    c = niwis_const
    pairs: list[tuple[str, str]] = []

    def add(endpoint: str, names: Iterable[str]) -> None:
        pairs.extend((endpoint, name) for name in names)

    add(
        c.DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC,
        c.HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_STATIC_QUANTITY.values(),
    )
    add(
        c.DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC,
        c.HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_DYNAMIC_QUANTITY.values(),
    )
    add(
        c.DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC,
        c.HYDRO_TO_NIWIS_DECILES_QUANTITY.values(),
    )
    add(
        c.DERIVED_ENDPOINT_CATEGORY,
        c.HYDRO_TO_NIWIS_OFFICIAL_DEVELOPMENT_7D_QUANTITY.values(),
    )
    add(c.DERIVED_ENDPOINT_CATEGORY, c.HYDRO_TO_NIWIS_DATED_EXTREME_QUANTITY.values())
    add(c.DERIVED_ENDPOINT_CATEGORY, c.HYDRO_TO_NIWIS_BELOW_GLW_QUANTITY.values())
    add(
        c.DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
        (
            name
            for key, name in c.HISTORICAL_STATISTIC_NIWIS_NAMES.items()
            if key not in c.HYDRO_TO_NIWIS_DATED_EXTREME_QUANTITY
        ),
    )
    add(c.DERIVED_ENDPOINT_HISTORICAL_STATISTICS, c.HYDRO_TO_NIWIS_SUM_QUANTITY.values())
    add(c.DERIVED_ENDPOINT_HISTORICAL_STATISTICS, [c.DAYS_BELOW_GLW_NIWIS_NAME])
    add(
        c.DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
        c.HYDRO_TO_NIWIS_DEPTH_BELOW_GROUND_QUANTITY.values(),
    )
    add(
        c.DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS,
        c.CALENDAR_DAY_STATISTIC_NIWIS_NAMES.values(),
    )
    return pairs


def check_catalogue(derived_quantities: list[dict[str, Any]]) -> list[str]:
    """Return the problems between the integration's needs and NIWIS's catalogue."""
    endpoints_by_name: dict[str, set[str]] = {}
    for quantity in derived_quantities:
        endpoints_by_name.setdefault(quantity["abgeleiteteGroesse"], set()).add(
            quantity["endpunkt"]
        )

    problems: list[str] = []
    for endpoint, name in expected_quantities():
        offered = endpoints_by_name.get(name)
        if offered is None:
            problems.append(f"missing: {name!r} (expected on {endpoint})")
        elif endpoint not in offered:
            problems.append(
                f"moved: {name!r} is now on {sorted(offered)}, expected {endpoint}"
            )
    return problems


def check_karte(measurement_type: str, stations: Any) -> list[str]:
    """Return the problems with one map-classification list."""
    if not isinstance(stations, list) or not stations:
        return [f"karte/{measurement_type}: response is not a non-empty list"]

    problems: list[str] = []
    seen_classes: set[str] = set()
    for entry in stations:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("nummer"), str)
            or not isinstance(entry.get("niedrigwasserKlasse"), str)
        ):
            problems.append(
                f"karte/{measurement_type}: entry without nummer/niedrigwasserKlasse: "
                f"{entry!r}"
            )
            break
        seen_classes.add(entry["niedrigwasserKlasse"])

    unknown = sorted(seen_classes - KNOWN_KARTE_CLASSES)
    if unknown:
        problems.append(f"karte/{measurement_type}: unknown class value(s) {unknown}")
    return problems


async def _check_live() -> list[str]:
    """Run every check against the live NIWIS API."""
    async with ClientSession() as session:
        client = NiwisClient(session)
        problems: list[str] = []

        try:
            problems.extend(check_catalogue(await client.async_get_derived_quantities()))
        except NiwisError as err:
            problems.append(f"derived-quantity catalogue request failed: {err}")

        for measurement_type, messgroesse in (
            niwis_const.HYDRO_TO_NIWIS_KARTE_MESSGROESSE.items()
        ):
            try:
                stations = await client.async_get_karte_stations(
                    messgroesse, niwis_const.KARTE_KLASSIFIKATIONSART
                )
            except NiwisError as err:
                problems.append(f"karte/{measurement_type} request failed: {err}")
                continue
            problems.extend(check_karte(measurement_type, stations))

        return problems


def main() -> int:
    """Run the check and print a report; return the process exit code."""
    problems = asyncio.run(_check_live())

    if not problems:
        print(
            f"OK: all {len(expected_quantities())} derived quantities and the "
            "map-classification endpoint match what Hydro Monitor requests."
        )
        return 0

    print(f"NIWIS API drift detected ({len(problems)} problem(s)):")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

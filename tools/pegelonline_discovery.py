"""Capture real PEGELONLINE responses as test fixtures and a field summary.

Writes to `pegelonline_inventory/`:

* `stations_sample.json`: a handful of stations chosen to cover the cases
  the provider has to handle (see `_pick_samples`),
* `summary.json`: what the full station list contains (series, units,
  intervals, status values), so assumptions can be re-checked,
* `measurements/<uuid>__<series>.json` (31 days of raw values) and
  `timeseries/<uuid>__<series>.json` (the series with its unit and current
  measurement, incl. the MNW/MHW status): the responses for the samples,
* `errors.json`: how the service answers for unknown stations and series.

Run from the repository root:

    python -m tools.pegelonline_discovery
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any

from aiohttp import ClientSession

from custom_components.hydro_monitor.providers.pegelonline.const import (
    BASE_URL,
    HISTORY_PERIOD,
    STATIONS_ENDPOINT,
)

DEFAULT_OUTPUT_DIR = Path("pegelonline_inventory")
# One station keeps its full 31 days (about 3000 points) for the trend and
# statistics tests; the others keep only their newest points so the fixtures
# stay small (a 1-minute station has about 45000 points).
FULL_HISTORY_SAMPLE = "kaub_w_and_q"
SAMPLE_POINTS = 400
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Home Assistant Hydro Monitor discovery",
}


def _series(station: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a station's time series by short name."""
    return {item["shortname"]: item for item in station.get("timeseries", [])}


def _pick_samples(stations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Pick one station per case the provider must handle."""
    by_name = {station["shortname"]: station for station in stations}
    picks: dict[str, dict[str, Any]] = {}

    def first(label: str, predicate) -> None:
        for station in stations:
            if station not in picks.values() and predicate(station):
                picks[label] = station
                return

    picks["kaub_w_and_q"] = by_name["KAUB"]
    first(
        "one_minute_interval",
        lambda s: _series(s).get("W", {}).get("equidistance") == 1,
    )
    first(
        "hamburg_tidal",
        lambda s: s["longname"].startswith("HAMBURG")
        and "W" in _series(s),
    )
    first(
        "unit_metres_above_datum",
        lambda s: _series(s).get("W", {}).get("unit") == "m+NN"
        and "latitude" in s,
    )
    first("without_coordinates", lambda s: "latitude" not in s)
    first(
        "without_w_and_q",
        lambda s: "W" not in _series(s) and "Q" not in _series(s),
    )
    first(
        "discharge_only",
        lambda s: "Q" in _series(s) and "W" not in _series(s),
    )
    for state in ("low", "normal", "unknown", "commented", "high"):
        first(
            f"state_mnw_mhw_{state}",
            lambda s, state=state: _series(s).get("W", {})
            .get("currentMeasurement", {})
            .get("stateMnwMhw")
            == state,
        )
    return picks


def _summarise(stations: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe what the full station list contains."""
    series_names: Counter[str] = Counter()
    units: dict[str, Counter[str]] = {}
    intervals: dict[str, Counter[int]] = {}
    states: dict[str, Counter[str]] = {"stateMnwMhw": Counter(), "stateNswHsw": Counter()}
    keys: Counter[str] = Counter()

    for station in stations:
        keys.update(station.keys())
        for item in station.get("timeseries", []):
            name = item["shortname"]
            series_names[name] += 1
            units.setdefault(name, Counter())[str(item.get("unit"))] += 1
            intervals.setdefault(name, Counter())[item.get("equidistance")] += 1
            if name == "W":
                current = item.get("currentMeasurement") or {}
                for state in states:
                    states[state][str(current.get(state))] += 1

    return {
        "stations": len(stations),
        "station_keys": dict(keys),
        "without_coordinates": sum(1 for s in stations if "latitude" not in s),
        "without_w_and_q": sum(
            1 for s in stations if "W" not in _series(s) and "Q" not in _series(s)
        ),
        "series_counts": dict(series_names.most_common()),
        "units_by_series": {k: dict(v) for k, v in units.items()},
        "equidistance_by_series": {k: dict(v) for k, v in intervals.items()},
        "water_level_states": {k: dict(v) for k, v in states.items()},
    }


def _write(path: Path, data: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


async def _get(session: ClientSession, path: str, **params: str) -> tuple[int, Any]:
    async with session.get(
        f"{BASE_URL}/{path}", params=params, headers=HEADERS, timeout=60
    ) as response:
        try:
            body = await response.json(content_type=None)
        except ValueError:
            body = await response.text()
        return response.status, body


async def _discover(output_dir: Path) -> None:
    async with ClientSession() as session:
        status, stations = await _get(
            session,
            STATIONS_ENDPOINT,
            includeTimeseries="true",
            includeCurrentMeasurement="true",
        )
        if status != 200 or not isinstance(stations, list):
            raise SystemExit(f"Station list failed: HTTP {status}")

        samples = _pick_samples(stations)
        _write(output_dir / "summary.json", _summarise(stations))
        _write(
            output_dir / "stations_sample.json",
            {label: station for label, station in sorted(samples.items())},
        )

        for label, station in samples.items():
            for name in ("W", "Q"):
                if name not in _series(station):
                    continue
                uuid = station["uuid"]
                for folder, path, params in (
                    ("measurements", f"stations/{uuid}/{name}/measurements.json", {"start": HISTORY_PERIOD}),
                    (
                        "timeseries",
                        f"stations/{uuid}/{name}.json",
                        {"includeCurrentMeasurement": "true"},
                    ),
                ):
                    status, body = await _get(session, path, **params)
                    if status == 200:
                        if (
                            folder == "measurements"
                            and label != FULL_HISTORY_SAMPLE
                            and isinstance(body, list)
                        ):
                            body = body[-SAMPLE_POINTS:]
                        _write(
                            output_dir / folder / f"{uuid}__{name}.json",
                            body,
                            compact=folder == "measurements",
                        )
                    else:
                        print(f"{label} {folder} {name}: HTTP {status}")

        errors: dict[str, Any] = {}
        unknown = "00000000-0000-0000-0000-000000000000"
        kaub = samples["kaub_w_and_q"]["uuid"]
        for label, path in (
            ("unknown_station_timeseries", f"stations/{unknown}/W.json"),
            ("unknown_station_measurements", f"stations/{unknown}/W/measurements.json"),
            ("unknown_series_measurements", f"stations/{kaub}/XX/measurements.json"),
            ("malformed_station_id", "stations/not-a-uuid/W.json"),
        ):
            status, body = await _get(session, path)
            errors[label] = {"path": path, "status": status, "body": body}
        _write(output_dir / "errors.json", errors)

        print(f"Wrote {len(samples)} sample stations to {output_dir}")


def main() -> None:
    """Run the discovery."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    asyncio.run(_discover(args.output_dir))


if __name__ == "__main__":
    main()

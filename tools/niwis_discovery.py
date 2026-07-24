"""Inspect the public NIWIS API and generate a field inventory."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aiohttp import ClientSession

from custom_components.hydro_monitor.models import HydroMeasurementType
from custom_components.hydro_monitor.providers.niwis.api import (
    NiwisClient,
    NiwisError,
)
from custom_components.hydro_monitor.providers.niwis.const import (
    HYDRO_TO_NIWIS_ENDPOINT,
)
from custom_components.hydro_monitor.providers.niwis.mapper import (
    station_from_niwis,
)

DEFAULT_OUTPUT_DIR = Path("niwis_inventory")
SERIES_DAYS = 30
DEFAULT_STATIONS_PER_TYPE = 10

DERIVED_REFERENCE_START_YEAR = 1991
DERIVED_REFERENCE_END_YEAR = 2020
DERIVED_YEAR_DEFINITION = "KALENDERJAHR"
DERIVED_INTERVAL_DAYS = 30

NIWIS_DERIVED_TO_HYDRO_TYPE = {
    "ABFLUSS": HydroMeasurementType.DISCHARGE,
    "WASSERSTAND": HydroMeasurementType.WATER_LEVEL,
    "GRUNDWASSER": HydroMeasurementType.GROUNDWATER_LEVEL,
    "QUELLSCHUETTUNG": HydroMeasurementType.SPRING_DISCHARGE,
}

DERIVED_ENDPOINTS_WITHOUT_PARAMETERS = {
    "berechneKlimaindikatorNiedrigwassertage",
    "berechneKlimaindikatorMonatlicheAbweichungenMittelwert",
}


def _json_type(value: Any) -> str:
    """Return a readable JSON value type."""
    if value is None:
        return "null"

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "number"

    if isinstance(value, str):
        return "string"

    if isinstance(value, list):
        return "array"

    if isinstance(value, dict):
        return "object"

    return type(value).__name__


def _collect_fields(
    records: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Collect field occurrence, value coverage and type information."""
    record_list = list(records)
    record_count = len(record_list)

    field_types: dict[str, set[str]] = defaultdict(set)
    field_counts: dict[str, int] = defaultdict(int)
    non_null_counts: dict[str, int] = defaultdict(int)
    examples: dict[str, Any] = {}

    for record in record_list:
        for key, value in record.items():
            field_counts[key] += 1
            field_types[key].add(_json_type(value))

            if value is not None:
                non_null_counts[key] += 1

                if key not in examples:
                    examples[key] = value

    return {
        key: {
            "types": sorted(field_types[key]),
            "present_in_records": field_counts[key],
            "non_null_records": non_null_counts[key],
            "total_records": record_count,
            "optional": field_counts[key] < record_count,
            "non_null_coverage_percent": (
                round(non_null_counts[key] / record_count * 100, 1)
                if record_count
                else 0.0
            ),
            "example": examples.get(key),
        }
        for key in sorted(field_types)
    }


def _collect_series_quality(
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Collect quality statistics for NIWIS time-series records."""
    record_list = list(records)

    invalid_values = {
        -777.0,
        -888.0,
        -999.0,
        -9999.0,
    }

    total_values = 0
    valid_values = 0
    invalid_measurement_values = 0
    missing_measurement_values = 0

    flags: dict[str, int] = defaultdict(int)
    units: dict[str, int] = defaultdict(int)
    stations: dict[str, dict[str, Any]] = {}

    for record in record_list:
        station_id = str(record.get("messstelleNr") or "")
        value = record.get("messwert")
        flag = record.get("flag")
        unit = record.get("einheit")

        station_quality = stations.setdefault(
            station_id,
            {
                "total_values": 0,
                "valid_values": 0,
                "invalid_values": 0,
                "flags": defaultdict(int),
                "units": defaultdict(int),
            },
        )

        total_values += 1
        station_quality["total_values"] += 1

        if unit is not None:
            unit_text = str(unit)
            units[unit_text] += 1
            station_quality["units"][unit_text] += 1

        if flag is not None:
            flag_text = str(flag)
            flags[flag_text] += 1
            station_quality["flags"][flag_text] += 1

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            numeric_value = None

        if numeric_value is None:
            missing_measurement_values += 1
            station_quality["invalid_values"] += 1
            continue

        if numeric_value in invalid_values or numeric_value <= -700:
            invalid_measurement_values += 1
            station_quality["invalid_values"] += 1
            continue

        valid_values += 1
        station_quality["valid_values"] += 1

    invalid_values_total = invalid_measurement_values + missing_measurement_values

    station_rows = []

    for station_id, details in sorted(stations.items()):
        total = details["total_values"]
        valid = details["valid_values"]

        station_rows.append(
            {
                "station_id": station_id,
                "total_values": total,
                "valid_values": valid,
                "invalid_values": details["invalid_values"],
                "valid_coverage_percent": (
                    round(valid / total * 100, 1) if total else 0.0
                ),
                "flags": dict(sorted(details["flags"].items())),
                "units": dict(sorted(details["units"].items())),
            }
        )

    return {
        "total_values": total_values,
        "valid_values": valid_values,
        "invalid_values": invalid_values_total,
        "invalid_measurement_values": invalid_measurement_values,
        "missing_measurement_values": missing_measurement_values,
        "valid_coverage_percent": (
            round(valid_values / total_values * 100, 1) if total_values else 0.0
        ),
        "flags": dict(sorted(flags.items())),
        "units": dict(sorted(units.items())),
        "stations": station_rows,
    }


def _safe_filename(value: str) -> str:
    """Return a filesystem-safe filename."""
    safe_characters = []

    for character in value:
        if character.isalnum():
            safe_characters.append(character.lower())
        elif character in {" ", "-", "_"}:
            safe_characters.append("_")

    filename = "".join(safe_characters)

    while "__" in filename:
        filename = filename.replace("__", "_")

    return filename.strip("_") or "unnamed"


async def _probe_derived_quantities(
    client: NiwisClient,
    output_dir: Path,
    derived_quantities: list[dict[str, Any]],
    selected_stations: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Probe all advertised NIWIS derived quantities."""
    today = datetime.now(UTC).date()
    interval_start = today - timedelta(days=DERIVED_INTERVAL_DAYS)

    results: list[dict[str, Any]] = []

    for item in derived_quantities:
        name = str(item["abgeleiteteGroesse"])
        measurement = str(item["messgroesse"])
        endpoint = str(item["endpunkt"])

        result_record: dict[str, Any] = {
            "abgeleiteteGroesse": name,
            "messgroesse": measurement,
            "endpunkt": endpoint,
            "success": False,
            "station_id": None,
            "parameters": {},
            "response_type": None,
            "error": None,
        }

        params: dict[str, str] = {}

        if endpoint not in DERIVED_ENDPOINTS_WITHOUT_PARAMETERS:
            measurement_type = NIWIS_DERIVED_TO_HYDRO_TYPE.get(measurement)

            if measurement_type is None:
                result_record["error"] = f"Unsupported measurement type: {measurement}"
                results.append(result_record)
                continue

            stations = selected_stations.get(
                measurement_type.value,
                [],
            )

            if not stations:
                result_record["error"] = "No representative station available"
                results.append(result_record)
                continue

            station_id = str(stations[0]["messstelleNr"])
            result_record["station_id"] = station_id

            params = {
                "abgeleiteteGroesse": name,
                "messstelleNr": station_id,
            }

            if item.get("benoetigtReferenzzeitraum"):
                params.update(
                    {
                        "jahresdefinition": DERIVED_YEAR_DEFINITION,
                        "startJahr": str(DERIVED_REFERENCE_START_YEAR),
                        "endJahr": str(DERIVED_REFERENCE_END_YEAR),
                    }
                )

            if item.get("benoetigtZeitintervall"):
                params.update(
                    {
                        "von": interval_start.isoformat(),
                        "bis": today.isoformat(),
                    }
                )

        result_record["parameters"] = params

        try:
            response = await client.async_get_derived_result(
                endpoint,
                params=params or None,
            )
        except NiwisError as err:
            result_record["error"] = str(err)
        else:
            result_record["success"] = True
            result_record["response_type"] = _json_type(response)

            result_filename = f"{measurement.lower()}__{_safe_filename(name)}.json"

            _write_json(
                output_dir / "derived_results" / endpoint / result_filename,
                response,
            )

            result_record["response_file"] = str(
                Path("derived_results") / endpoint / result_filename
            )

        results.append(result_record)

    return results


def _write_json(path: Path, data: Any) -> None:
    """Write formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_fields_csv(
    output_dir: Path,
    inventories: dict[str, dict[str, dict[str, Any]]],
) -> None:
    """Write a combined CSV field inventory."""
    csv_path = output_dir / "fields.csv"

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "dataset",
                "field",
                "types",
                "present_in_records",
                "non_null_records",
                "total_records",
                "optional",
                "non_null_coverage_percent",
                "example",
            ]
        )

        for dataset, fields in sorted(inventories.items()):
            for field_name, details in fields.items():
                writer.writerow(
                    [
                        dataset,
                        field_name,
                        ", ".join(details["types"]),
                        details["present_in_records"],
                        details["non_null_records"],
                        details["total_records"],
                        details["optional"],
                        details["non_null_coverage_percent"],
                        json.dumps(
                            details["example"],
                            ensure_ascii=False,
                            default=str,
                        ),
                    ]
                )


def _write_markdown(
    output_dir: Path,
    selected_stations: dict[str, list[dict[str, Any]]],
    inventories: dict[str, dict[str, dict[str, Any]]],
    series_quality: dict[str, dict[str, Any]],
    derived_quantities: list[dict[str, Any]],
    derived_probe_results: list[dict[str, Any]],
) -> None:
    """Write a human-readable Markdown report."""
    lines = [
        "# NIWIS API Inventory",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "## Representative stations",
        "",
        "| Measurement type | Station ID | Station name |",
        "|---|---|---|",
    ]

    for measurement_type, stations in sorted(selected_stations.items()):
        for station in stations:
            lines.append(
                "| "
                f"{measurement_type} | "
                f"{station.get('messstelleNr', '')} | "
                f"{station.get('name', '')} |"
            )

    lines.extend(
        [
            "",
            "## Datasets and fields",
            "",
        ]
    )

    for dataset, fields in sorted(inventories.items()):
        lines.extend(
            [
                f"### `{dataset}`",
                "",
                "| Field | Types | Present | Non-null | Coverage | Example |",
                "|---|---|---:|---:|---:|---|",
            ]
        )

        for field_name, details in fields.items():
            example = json.dumps(
                details["example"],
                ensure_ascii=False,
                default=str,
            )

            if len(example) > 100:
                example = example[:97] + "..."

            lines.append(
                "| "
                f"`{field_name}` | "
                f"{', '.join(details['types'])} | "
                f"{details['present_in_records']}/{details['total_records']} | "
                f"{details['non_null_records']}/{details['total_records']} | "
                f"{details['non_null_coverage_percent']:.1f}% | "
                f"`{example}` |"
            )

        lines.append("")

    successful_probes = sum(1 for result in derived_probe_results if result["success"])

    lines.extend(
        [
            "## Derived quantity probe results",
            "",
            (f"Successful: {successful_probes}/{len(derived_probe_results)}"),
            "",
            "| Name | Measurement | Endpoint | Station | Success | Response | Error |",
            "|---|---|---|---|---:|---|---|",
        ]
    )

    for result in derived_probe_results:
        error = str(result.get("error") or "")

        if len(error) > 120:
            error = error[:117] + "..."

        lines.append(
            "| "
            f"{result['abgeleiteteGroesse']} | "
            f"{result['messgroesse']} | "
            f"`{result['endpunkt']}` | "
            f"{result.get('station_id') or ''} | "
            f"{'yes' if result['success'] else 'no'} | "
            f"{result.get('response_type') or ''} | "
            f"`{error}` |"
        )

    lines.append("")

    lines.extend(
        [
            "## Derived quantities",
            "",
            "| Name | Measurement | Reference period | Time interval | Endpoint |",
            "|---|---|---:|---:|---|",
        ]
    )

    for item in sorted(
        derived_quantities,
        key=lambda value: (
            str(value.get("messgroesse") or ""),
            str(value.get("abgeleiteteGroesse") or ""),
        ),
    ):
        lines.append(
            "| "
            f"{item.get('abgeleiteteGroesse', '')} | "
            f"{item.get('messgroesse', '')} | "
            f"{'yes' if item.get('benoetigtReferenzzeitraum') else 'no'} | "
            f"{'yes' if item.get('benoetigtZeitintervall') else 'no'} | "
            f"`{item.get('endpunkt', '')}` |"
        )

    lines.append("")

    lines.extend(
        [
            "## Time-series quality",
            "",
            "| Measurement type | Total | Valid | Invalid | Coverage | Flags | Units |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
    )

    for measurement_type, quality in sorted(series_quality.items()):
        flags = (
            ", ".join(f"{flag}: {count}" for flag, count in quality["flags"].items())
            or "none"
        )

        units = (
            ", ".join(f"{unit}: {count}" for unit, count in quality["units"].items())
            or "none"
        )

        lines.append(
            "| "
            f"{measurement_type} | "
            f"{quality['total_values']} | "
            f"{quality['valid_values']} | "
            f"{quality['invalid_values']} | "
            f"{quality['valid_coverage_percent']:.1f}% | "
            f"{flags} | "
            f"{units} |"
        )

    lines.append("")

    for measurement_type, quality in sorted(series_quality.items()):
        lines.extend(
            [
                f"### `{measurement_type}` station quality",
                "",
                "| Station ID | Total | Valid | Invalid | Coverage | Flags |",
                "|---|---:|---:|---:|---:|---|",
            ]
        )

        for station in quality["stations"]:
            flags = (
                ", ".join(
                    f"{flag}: {count}" for flag, count in station["flags"].items()
                )
                or "none"
            )

            lines.append(
                "| "
                f"{station['station_id']} | "
                f"{station['total_values']} | "
                f"{station['valid_values']} | "
                f"{station['invalid_values']} | "
                f"{station['valid_coverage_percent']:.1f}% | "
                f"{flags} |"
            )

        lines.append("")

    (output_dir / "inventory.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


async def _discover(
    output_dir: Path,
    *,
    stations_per_type: int,
) -> None:
    """Fetch NIWIS datasets and generate the inventory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    async with ClientSession() as session:
        client = NiwisClient(session)

        catalog = await client.async_get_station_catalog()
        _write_json(output_dir / "catalog.json", catalog)

        derived_quantities = await client.async_get_derived_quantities()
        _write_json(
            output_dir / "derived_quantities.json",
            derived_quantities,
        )

        inventories: dict[str, dict[str, dict[str, Any]]] = {
            "catalog": _collect_fields(catalog),
            "derived_quantities": _collect_fields(derived_quantities),
        }

        series_quality: dict[str, dict[str, Any]] = {}

        selected_stations: dict[str, list[dict[str, Any]]] = {
            measurement_type.value: [] for measurement_type in HydroMeasurementType
        }

        for raw_station in catalog:
            try:
                station = station_from_niwis(raw_station)
            except (KeyError, TypeError, ValueError):
                continue

            for measurement_type in station.measurement_types:
                stations = selected_stations[measurement_type.value]
                station_id = str(raw_station["messstelleNr"])

                already_selected = any(
                    str(selected_station["messstelleNr"]) == station_id
                    for selected_station in stations
                )

                if not already_selected and len(stations) < stations_per_type:
                    stations.append(raw_station)

            if all(
                len(stations) >= stations_per_type
                for stations in selected_stations.values()
            ):
                break

        derived_probe_results = await _probe_derived_quantities(
            client,
            output_dir,
            derived_quantities,
            selected_stations,
        )

        _write_json(
            output_dir / "derived_probe_results.json",
            derived_probe_results,
        )

        for measurement_type in HydroMeasurementType:
            raw_stations = selected_stations[measurement_type.value]

            if not raw_stations:
                print(f"No representative stations found for {measurement_type.value}")
                continue

            station_details_records: list[dict[str, Any]] = []
            series_records: list[dict[str, Any]] = []

            endpoint = HYDRO_TO_NIWIS_ENDPOINT[measurement_type.value]

            for raw_station in raw_stations:
                station_id = str(raw_station["messstelleNr"])

                try:
                    station_details = await client.async_get_station(station_id)
                except NiwisError as err:
                    print(
                        "Could not fetch station details for "
                        f"{measurement_type.value} / {station_id}: {err}"
                    )
                    continue

                station_details_records.append(station_details)

                _write_json(
                    output_dir
                    / "stations"
                    / measurement_type.value
                    / f"{station_id}.json",
                    station_details,
                )

                try:
                    series = await client.async_get_series(
                        endpoint,
                        station_id,
                        days=SERIES_DAYS,
                    )
                except NiwisError as err:
                    print(
                        "Could not fetch series for "
                        f"{measurement_type.value} / {station_id}: {err}"
                    )
                    continue

                series_records.extend(series)

                _write_json(
                    output_dir
                    / "series"
                    / measurement_type.value
                    / f"{station_id}.json",
                    series,
                )

            inventories[f"station_{measurement_type.value}"] = _collect_fields(
                station_details_records
            )

            inventories[f"series_{measurement_type.value}"] = _collect_fields(
                series_records
            )

            series_quality[measurement_type.value] = _collect_series_quality(
                series_records
            )

        _write_json(
            output_dir / "series_quality.json",
            series_quality,
        )

        _write_json(
            output_dir / "schemas.json",
            inventories,
        )
        _write_fields_csv(output_dir, inventories)
        _write_markdown(
            output_dir,
            selected_stations,
            inventories,
            series_quality,
            derived_quantities,
            derived_probe_results,
        )

    print(f"NIWIS inventory written to: {output_dir.resolve()}")


def main() -> None:
    """Run the NIWIS discovery tool."""
    parser = argparse.ArgumentParser(
        description=("Inspect the public NIWIS API and generate a field inventory.")
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(f"Directory for generated files (default: {DEFAULT_OUTPUT_DIR})"),
    )
    parser.add_argument(
        "--stations-per-type",
        type=int,
        default=DEFAULT_STATIONS_PER_TYPE,
        help=(
            "Number of representative stations to inspect per "
            f"measurement type (default: {DEFAULT_STATIONS_PER_TYPE})"
        ),
    )
    args = parser.parse_args()
    asyncio.run(
        _discover(
            args.output_dir,
            stations_per_type=args.stations_per_type,
        )
    )


if __name__ == "__main__":
    main()

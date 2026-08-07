"""Map NIWIS API data to provider-neutral Hydro Monitor models."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

from ...models import (
    HydroLowWaterBoundaries,
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from .const import LOW_WATER_CLASS_KEYS, LOW_WATER_CLASS_LABEL_TO_KEY, NIWIS_TO_HYDRO_TYPE


def as_float(value: Any) -> float | None:
    """Convert a NIWIS value to float."""
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    """Parse a NIWIS date value."""
    if value in (None, ""):
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _is_valid_measurement(value: float | None) -> bool:
    """Return whether a NIWIS measurement is usable.

    NIWIS uses large negative values such as -777 as technical placeholders.
    Reject the complete placeholder range instead of only exact sentinel values.
    """
    return value is not None and value > -700.0


def station_from_niwis(
    data: dict[str, Any],
    distance_km: float | None = None,
) -> HydroStation:
    """Map a NIWIS station record."""
    measurement_types = tuple(
        HydroMeasurementType(NIWIS_TO_HYDRO_TYPE[item])
        for item in data.get("messgroesse", [])
        if item in NIWIS_TO_HYDRO_TYPE
    )

    return HydroStation(
        provider="niwis",
        station_id=str(data["messstelleNr"]),
        name=str(data.get("name") or data["messstelleNr"]),
        measurement_types=measurement_types,
        latitude=as_float(data.get("breite")),
        longitude=as_float(data.get("laenge")),
        country_code=data.get("landcode"),
        station_type=data.get("messstellentyp"),
        locality=data.get("ortslage"),
        waterbody=data.get("gewaesser"),
        waterbody_code=(str(data["gkz"]) if data.get("gkz") is not None else None),
        waterbody_position=data.get("lageGewaesser"),
        catchment_area_km2=as_float(data.get("ezgGroesse")),
        elevation_ground=as_float(data.get("hoeheGok")),
        gauge_zero_elevation=as_float(data.get("hoehePnp")),
        elevation_system=data.get("hoehensystem"),
        hydrogeological_region=data.get("teilraumName"),
        hydrogeological_region_code=data.get("teilraumNr"),
        operator=data.get("betreiber"),
        operator_url=data.get("urlBetreiber"),
        institution=data.get("institution"),
        institution_url=data.get("urlInstitution"),
        source_url=data.get("urlMessstelle"),
        license_name=data.get("lizenz"),
        remarks=data.get("bemerkung"),
        historical_low_discharge=as_float(data.get("nnq")),
        historical_low_discharge_date=_parse_date(data.get("nnqDatum")),
        historical_low_water_level=as_float(data.get("nnw")),
        historical_low_water_level_date=_parse_date(data.get("nnwDatum")),
        distance_km=distance_km,
    )


def _low_water_class_key(label: str) -> str | None:
    """Map one NIWIS German low-water label to a stable English option key.

    NIWIS is inconsistent about capitalization of "kein Niedrigwasser"
    across endpoints, so the lookup is case-insensitive.
    """
    return LOW_WATER_CLASS_LABEL_TO_KEY.get(label.strip().casefold())


def _single_category_result_from_niwis(
    data: Any,
) -> tuple[str | None, str | None, bool]:
    """Map a berechneEinzelwertKategorie envelope's common fields.

    Returns (raw_label, error, suppressed). suppressed is True when NIWIS
    flagged hatZuvieleFehlwerte or returned a non-empty fehlermeldung --
    callers should treat their mapped/authoritative value as unavailable in
    that case, while still exposing the raw label and error for
    transparency. Shared by every quantity served through this endpoint's
    einzelwert/fehlermeldung/hatZuvieleFehlwerte envelope.
    """
    if not isinstance(data, dict):
        return None, None, False

    raw_error = data.get("fehlermeldung")
    error = raw_error if isinstance(raw_error, str) and raw_error.strip() else None

    raw_value = data.get("einzelwert")
    raw_label = raw_value if isinstance(raw_value, str) and raw_value.strip() else None

    suppressed = error is not None or bool(data.get("hatZuvieleFehlwerte"))
    return raw_label, error, suppressed


def low_water_class_from_niwis(
    data: Any,
) -> tuple[str | None, str | None, str | None]:
    """Map a berechneEinzelwertKategorie result to (class_key, raw_label, error).

    hatZuvieleFehlwerte or a non-empty fehlermeldung take priority over any
    co-present einzelwert for the mapped class (no observed sample has both
    set; treat as an unverified-but-conservative assumption, revisit if
    seen). The raw label is preserved whenever present, even when the
    mapped class is suppressed, so nothing NIWIS returned is silently
    discarded.
    """
    raw_label, error, suppressed = _single_category_result_from_niwis(data)

    if suppressed:
        return None, raw_label, error

    if raw_label is None:
        return None, None, error

    return _low_water_class_key(raw_label), raw_label, error


def official_development_7d_from_niwis(
    data: Any,
) -> tuple[str | None, str | None, str | None]:
    """Map a berechneEinzelwertKategorie 'Entwicklung letzte 7 Tage' result.

    Same envelope and priority rules as low_water_class_from_niwis, but no
    label-to-key mapping is applied yet: NIWIS's development-direction
    vocabulary is unconfirmed (only "gleichbleibend" observed so far), so
    the value is exposed as-is (raw label == value). See ADR-005 in
    docs/niwis_reference.md ("preserve unknown values").
    """
    raw_label, error, suppressed = _single_category_result_from_niwis(data)

    if suppressed:
        return None, raw_label, error

    if raw_label is None:
        return None, None, error

    return raw_label, raw_label, error


def day_of_year_index(reference_date: date) -> int:
    """Return a 1-based index into NIWIS's fixed 366-row per-day boundary table.

    UNVERIFIED assumption (docs/niwis_reference.md §11.5, §7.16 item 10):
    NIWIS never labels rows with dates. schwellenwerteProTag always has
    exactly 366 rows, shaped like a leap-year calendar (row 60 = Feb 29).
    date.timetuple().tm_yday gives 1-366 for the *current* year but only
    accounts for a real Feb 29 in actual leap years; in non-leap years we
    add 1 for dates on/after 1 March to keep alignment with the table's
    leap-shaped layout.
    """
    day_of_year = reference_date.timetuple().tm_yday
    if not calendar.isleap(reference_date.year) and reference_date.month >= 3:
        day_of_year += 1
    return day_of_year


def _classification_keys_from_niwis(raw_labels: Any) -> tuple[str, ...] | None:
    """Map and validate a klassifikationen array against the known scheme.

    Returns None unless every label maps AND the result exactly equals the
    expected key set in the expected order -- guards against silently
    mis-aligning thresholds to bands, and against the shared/overloaded
    berechneKlassifikationsgrenzeDynamisch endpoint ever returning the
    10-class deciles shape here by mistake.
    """
    if not isinstance(raw_labels, list):
        return None

    keys = tuple(
        _low_water_class_key(label) if isinstance(label, str) else None
        for label in raw_labels
    )
    return keys if keys == LOW_WATER_CLASS_KEYS else None


def _boundary_thresholds(raw: Any, expected_count: int) -> tuple[float, ...] | None:
    """Validate and convert a flat threshold array to floats."""
    if not isinstance(raw, list) or len(raw) != expected_count:
        return None

    values = tuple(as_float(item) for item in raw)
    return None if None in values else values


def _boundary_row(rows: Any, reference_date: date) -> list[Any] | None:
    """Return the one row of a 366-row NIWIS per-day table for a date."""
    if not isinstance(rows, list) or len(rows) != 366:
        return None

    index = day_of_year_index(reference_date) - 1
    row = rows[index] if 0 <= index < len(rows) else None
    return row if isinstance(row, list) else None


def _boundary_error(data: dict[str, Any]) -> str | None:
    """Return a boundary result's NIWIS-reported error message, if any."""
    raw_error = data.get("fehlermeldung")
    return raw_error if isinstance(raw_error, str) and raw_error.strip() else None


def static_low_water_boundaries_from_niwis(data: Any) -> HydroLowWaterBoundaries:
    """Map a berechneKlassifikationsgrenzeStatisch result."""
    if not isinstance(data, dict):
        return HydroLowWaterBoundaries()

    error = _boundary_error(data)
    labels = _classification_keys_from_niwis(data.get("klassifikationen"))
    open_ended = data.get("beidseitigOffeneSchwellenwerte")
    open_ended = open_ended if isinstance(open_ended, bool) else None
    unit = data.get("einheit") if isinstance(data.get("einheit"), str) else None

    if error is not None or data.get("hatZuvieleFehlwerte"):
        return HydroLowWaterBoundaries(
            classification_labels=labels, open_ended=open_ended, static_error=error
        )

    if labels is None:
        return HydroLowWaterBoundaries(
            open_ended=open_ended,
            static_error="unrecognized classification labels",
        )

    thresholds = _boundary_thresholds(data.get("schwellenwerte"), len(labels) - 1)
    if thresholds is None:
        return HydroLowWaterBoundaries(
            classification_labels=labels,
            open_ended=open_ended,
            static_error="malformed schwellenwerte",
        )

    return HydroLowWaterBoundaries(
        classification_labels=labels,
        open_ended=open_ended,
        static_thresholds=thresholds,
        static_unit=unit,
    )


def dynamic_low_water_boundaries_from_niwis(
    data: Any,
    reference_date: date,
) -> HydroLowWaterBoundaries:
    """Map a berechneKlassifikationsgrenzeDynamisch result's 'today' row."""
    if not isinstance(data, dict):
        return HydroLowWaterBoundaries()

    error = _boundary_error(data)
    labels = _classification_keys_from_niwis(data.get("klassifikationen"))
    open_ended = data.get("beidseitigOffeneSchwellenwerte")
    open_ended = open_ended if isinstance(open_ended, bool) else None
    unit = data.get("einheit") if isinstance(data.get("einheit"), str) else None

    if error is not None or data.get("hatZuvieleFehlwerte"):
        return HydroLowWaterBoundaries(
            classification_labels=labels, open_ended=open_ended, dynamic_error=error
        )

    if labels is None:
        return HydroLowWaterBoundaries(
            open_ended=open_ended,
            dynamic_error="unrecognized classification labels",
        )

    row = _boundary_row(data.get("schwellenwerteProTag"), reference_date)
    if row is None:
        return HydroLowWaterBoundaries(
            classification_labels=labels,
            open_ended=open_ended,
            dynamic_error="missing per-day threshold row",
        )

    thresholds = _boundary_thresholds(row, len(labels) - 1)
    if thresholds is None:
        return HydroLowWaterBoundaries(
            classification_labels=labels,
            open_ended=open_ended,
            dynamic_error="malformed schwellenwerteProTag row",
        )

    return HydroLowWaterBoundaries(
        classification_labels=labels,
        open_ended=open_ended,
        dynamic_thresholds=thresholds,
        dynamic_unit=unit,
        dynamic_reference_date=reference_date,
    )


def observation_from_niwis(
    measurement_type: HydroMeasurementType,
    series: list[dict[str, Any]],
) -> HydroObservation:
    """Map the newest valid NIWIS observation and calculate trends.

    Technical NIWIS placeholder values such as -777 are ignored both
    for the current measurement and for historical trend values.
    """
    if not series:
        return HydroObservation(
            measurement_type,
            None,
            None,
            None,
        )

    valid_observations: list[tuple[date, dict[str, Any], float]] = []

    for item in series:
        value = as_float(item.get("messwert"))
        observed_on = _parse_date(item.get("datum"))

        if observed_on is None:
            continue

        if not _is_valid_measurement(value):
            continue

        valid_observations.append(
            (
                observed_on,
                item,
                value,
            )
        )

    if not valid_observations:
        return HydroObservation(
            measurement_type,
            None,
            None,
            None,
            sample_count=0,
        )

    valid_observations.sort(key=lambda observation: observation[0])

    observed_on, newest, value = valid_observations[-1]

    def value_at_or_before(
        target_date: date,
    ) -> float | None:
        """Return the newest valid value on or before a date."""
        for (
            observation_date,
            _item,
            observation_value,
        ) in reversed(valid_observations):
            if observation_date <= target_date:
                return observation_value

        return None

    value_1d = value_at_or_before(observed_on - timedelta(days=1))
    value_7d = value_at_or_before(observed_on - timedelta(days=7))

    change_1d = value - value_1d if value_1d is not None else None
    change_7d = value - value_7d if value_7d is not None else None

    observations_30d = [
        observation[2]
        for observation in valid_observations
        if observation[0] >= observed_on - timedelta(days=30)
    ]

    minimum_30d = min(observations_30d) if observations_30d else None

    maximum_30d = max(observations_30d) if observations_30d else None

    return HydroObservation(
        measurement_type,
        value,
        newest.get("einheit"),
        observed_on,
        newest.get("flag"),
        change_1d=change_1d,
        change_7d=change_7d,
        minimum_30d=minimum_30d,
        maximum_30d=maximum_30d,
        sample_count=len(valid_observations),
    )

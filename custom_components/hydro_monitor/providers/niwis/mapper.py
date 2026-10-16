"""Map NIWIS API data to provider-neutral Hydro Monitor models."""

from __future__ import annotations

import calendar
import math
import re
from datetime import date, timedelta
from typing import Any

from ...models import (
    HydroCalendarDayValue,
    HydroDatedExtreme,
    HydroDeciles,
    HydroDerivedValue,
    HydroLowWaterBoundaries,
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from .const import (
    DECILE_CLASS_LABELS,
    LOW_WATER_CLASS_KEYS,
    LOW_WATER_CLASS_LABEL_TO_KEY,
    NIWIS_TO_HYDRO_TYPE,
)


def as_float(value: Any) -> float | None:
    """Convert a NIWIS value to float, rejecting NaN.

    Python's float("NaN") succeeds and produces a real nan float rather
    than raising -- silently allowing that through would eventually surface
    as a NaN sensor state, breaking Home Assistant's state machine and
    long-term statistics. NIWIS is confirmed to return the literal string
    "NaN" for einzelwert on poor-quality derived results.
    """
    try:
        result = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _parse_date(value: Any) -> date | None:
    """Parse a NIWIS date value."""
    if value in (None, ""):
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _parse_german_date(value: str) -> date | None:
    """Parse a NIWIS DD.MM.YYYY date, used only by the 'mit Datum' quantities.

    Kept separate from _parse_date, which handles the ISO-formatted dates
    used everywhere else in the NIWIS API.
    """
    try:
        day, month, year = value.split(".")
        return date(int(year), int(month), int(day))
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
    """Map one NIWIS low-water label to a stable English option key.

    Two vocabularies reach here: the German labels of the classification-
    boundary endpoints ("extrem niedrig") and the upper-case enum of the map
    classification endpoint ("EXTREM_NIEDRIG"). NIWIS is also inconsistent
    about capitalization across endpoints, so the lookup normalises
    underscores to spaces and is case-insensitive.
    """
    return LOW_WATER_CLASS_LABEL_TO_KEY.get(
        label.strip().replace("_", " ").casefold()
    )


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


def low_water_class_from_karte(
    stations: Any,
    station_id: str,
) -> tuple[str | None, str | None, str | None]:
    """Map NIWIS's map-classification list to (class_key, raw_label, error).

    stations is the list returned by the karte/messstelle endpoint (one
    entry per station of a measurement type); the entry is looked up by
    nummer. The raw enum label is preserved whenever present, even when it
    does not map to a class key (e.g. KEINE_DATEN, which NIWIS's own map
    shows as "no data"), so nothing NIWIS returned is silently discarded
    (ADR-005 in docs/niwis_reference.md). An error is reported only for a
    malformed response or a station missing from the list.
    """
    if not isinstance(stations, list):
        return None, None, "malformed classification response"

    entry = next(
        (
            item
            for item in stations
            if isinstance(item, dict) and item.get("nummer") == station_id
        ),
        None,
    )
    if entry is None:
        return None, None, "station not in NIWIS classification data"

    raw_label = entry.get("niedrigwasserKlasse")
    if not isinstance(raw_label, str) or not raw_label.strip():
        return None, None, "no classification in NIWIS response"

    return _low_water_class_key(raw_label), raw_label, None


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


def _single_numeric_result_from_niwis(
    data: Any,
) -> tuple[float | None, str | None, str | None]:
    """Map a berechneEinzelwertNummer envelope's common fields.

    Returns (value, unit, error). Same fehlermeldung/hatZuvieleFehlwerte
    suppression-priority as _single_category_result_from_niwis; einzelwert
    goes through as_float() (rejects NaN, including the literal "NaN"
    string NIWIS returns on poor data quality). Kept separate from
    _single_category_result_from_niwis: same field names, different
    einzelwert type/NaN-handling, and einheit is meaningful here but not
    there.
    """
    if not isinstance(data, dict):
        return None, None, None

    raw_error = data.get("fehlermeldung")
    error = raw_error if isinstance(raw_error, str) and raw_error.strip() else None
    unit = data.get("einheit") if isinstance(data.get("einheit"), str) else None

    if error is not None or bool(data.get("hatZuvieleFehlwerte")):
        return None, unit, error

    return as_float(data.get("einzelwert")), unit, error


def historical_statistic_from_niwis(data: Any) -> HydroDerivedValue:
    """Map one berechneEinzelwertNummer result (MQ/MNQ/NM7Q/NM30Q/MW/MNW)."""
    value, unit, error = _single_numeric_result_from_niwis(data)
    return HydroDerivedValue(value=value, unit=unit, error=error)


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


def _decile_labels_from_niwis(raw_labels: Any) -> tuple[str, ...] | None:
    """Validate a klassifikationen array against the fixed decile label set.

    No key-mapping is applied (unlike _classification_keys_from_niwis):
    the labels ("0-10%" etc.) are already stable, language-neutral
    percentage-band identifiers with no German-to-English translation need.
    """
    if not isinstance(raw_labels, list):
        return None

    labels = tuple(raw_labels)
    return labels if labels == DECILE_CLASS_LABELS else None


def deciles_from_niwis(data: Any, reference_date: date) -> HydroDeciles:
    """Map a berechneKlassifikationsgrenzeDynamisch deciles result's 'today' row.

    Mirrors dynamic_low_water_boundaries_from_niwis's structure. Two
    deltas: labels are validated, not mapped to keys (see
    _decile_labels_from_niwis), and expected_count is len(labels) + 1
    rather than len(labels) - 1 -- deciles are the CLOSED/bounded variant
    of this endpoint's shape (beidseitigOffeneSchwellenwerte is False,
    confirmed via real captured samples), so its 11 threshold points
    include the reference period's absolute min/max in addition to the 9
    interior boundaries between the 10 classification_labels bands.
    """
    if not isinstance(data, dict):
        return HydroDeciles()

    error = _boundary_error(data)
    labels = _decile_labels_from_niwis(data.get("klassifikationen"))
    unit = data.get("einheit") if isinstance(data.get("einheit"), str) else None

    if error is not None or data.get("hatZuvieleFehlwerte"):
        return HydroDeciles(classification_labels=labels, error=error)

    if labels is None:
        return HydroDeciles(error="unrecognized classification labels")

    row = _boundary_row(data.get("schwellenwerteProTag"), reference_date)
    if row is None:
        return HydroDeciles(
            classification_labels=labels,
            error="missing per-day threshold row",
        )

    thresholds = _boundary_thresholds(row, len(labels) + 1)
    if thresholds is None:
        return HydroDeciles(
            classification_labels=labels,
            error="malformed schwellenwerteProTag row",
        )

    return HydroDeciles(
        classification_labels=labels,
        thresholds=thresholds,
        unit=unit,
        reference_date=reference_date,
    )


def calendar_day_value_from_niwis(
    data: Any,
    reference_date: date,
) -> HydroCalendarDayValue:
    """Map one berechneZeitreihenErgebnisNummer per-calendar-day result's 'today' row.

    Same day-of-year alignment as the boundary/decile tables (via
    day_of_year_index), but "werte" is a flat 366-element array where each
    element IS the day's value -- not a sub-array of thresholds like
    "schwellenwerteProTag" -- so _boundary_row isn't reusable here.
    """
    if not isinstance(data, dict):
        return HydroCalendarDayValue()

    error = _boundary_error(data)
    unit = data.get("einheit") if isinstance(data.get("einheit"), str) else None

    if error is not None or data.get("hatZuvieleFehlwerte"):
        return HydroCalendarDayValue(unit=unit, error=error)

    row = data.get("werte")
    if not isinstance(row, list) or len(row) != 366:
        return HydroCalendarDayValue(unit=unit, error="malformed werte array")

    index = day_of_year_index(reference_date) - 1
    value = as_float(row[index]) if 0 <= index < len(row) else None
    if value is None:
        return HydroCalendarDayValue(unit=unit, error="missing per-day value")

    return HydroCalendarDayValue(value=value, unit=unit, reference_date=reference_date)


_DATED_EXTREME_PATTERN = re.compile(
    r"^([\d.,]+)\s*\((\d{2}\.\d{2}\.\d{4})-(\d{2}\.\d{2}\.\d{4})\)$"
)


def dated_extreme_from_niwis(data: Any) -> HydroDatedExtreme:
    """Map a berechneEinzelwertKategorie NM7Q/NM30Q result.

    The composite string ("15.26 (15.07.2026-21.07.2026)") is parsed into
    a value and the date range it occurred in; the unit comes from the
    envelope's einheit (present since the 2026-10 NIWIS restructuring, when
    NM7Q/NM30Q moved to this endpoint and the separate "mit Datum"
    quantities disappeared). The raw label is preserved even on parse
    failure (ADR-005 in docs/niwis_reference.md), instead of silently
    discarding an unrecognized response shape.
    """
    raw_label, error, suppressed = _single_category_result_from_niwis(data)
    unit = (
        data.get("einheit")
        if isinstance(data, dict) and isinstance(data.get("einheit"), str)
        else None
    )

    if suppressed or raw_label is None:
        return HydroDatedExtreme(unit=unit, error=error, raw_label=raw_label)

    match = _DATED_EXTREME_PATTERN.match(raw_label.strip())
    if match is None:
        return HydroDatedExtreme(
            unit=unit, raw_label=raw_label, error="unrecognized format"
        )

    value = as_float(match.group(1))
    occurred_from = _parse_german_date(match.group(2))
    occurred_to = _parse_german_date(match.group(3))

    return HydroDatedExtreme(
        value=value,
        unit=unit,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        raw_label=raw_label,
    )


def below_glw_from_niwis(data: Any) -> tuple[str | None, str | None, str | None]:
    """Map a berechneEinzelwertKategorie 'unter GlW' result.

    Same envelope and raw-label-passthrough shape as
    official_development_7d_from_niwis: NIWIS's vocabulary beyond the one
    observed sample ("unterhalb") is unconfirmed, so no key mapping is
    applied yet.
    """
    raw_label, error, suppressed = _single_category_result_from_niwis(data)

    if suppressed:
        return None, raw_label, error

    if raw_label is None:
        return None, None, error

    return raw_label, raw_label, error


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

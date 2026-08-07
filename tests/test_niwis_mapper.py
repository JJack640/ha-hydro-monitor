"""Tests for the NIWIS data mapper."""

import json
from datetime import date
from pathlib import Path

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType
from custom_components.hydro_monitor.providers.niwis.mapper import (
    as_float,
    day_of_year_index,
    deciles_from_niwis,
    dynamic_low_water_boundaries_from_niwis,
    historical_statistic_from_niwis,
    low_water_class_from_niwis,
    observation_from_niwis,
    official_development_7d_from_niwis,
    static_low_water_boundaries_from_niwis,
    station_from_niwis,
)

INVENTORY_DIR = Path(__file__).resolve().parent.parent / "niwis_inventory"


def _observation(
    observed_on: str,
    value: float | str,
    *,
    unit: str = "m. ü. NHN",
    flag: str | None = None,
) -> dict[str, object]:
    """Create a NIWIS observation fixture."""
    return {
        "datum": observed_on,
        "messwert": value,
        "einheit": unit,
        "flag": flag,
    }


def _station(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS station fixture."""
    station: dict[str, object] = {
        "messstelleNr": "DESM_DEBY16607001",
        "name": "Inkofen",
        "messgroesse": ["Abfluss", "Wasserstand"],
        "breite": 48.460657,
        "laenge": 11.865527,
        "landcode": "DEBY",
        "messstellentyp": None,
        "ortslage": None,
        "gewaesser": "Amper",
        "gkz": 164,
        "lageGewaesser": "11.9",
        "ezgGroesse": 3097,
        "hoeheGok": None,
        "hoehePnp": 415.58,
        "hoehensystem": "DHHN12",
        "teilraumName": None,
        "teilraumNr": None,
        "betreiber": "WWA München",
        "urlBetreiber": None,
        "institution": "LfU BY",
        "urlInstitution": "https://www.gkd.bayern.de/de/",
        "urlMessstelle": "https://example.invalid/station",
        "lizenz": "cc-by/4.0",
        "bemerkung": "Example station",
        "nnq": 10.7,
        "nnqDatum": "1947-10-03",
        "nnw": None,
        "nnwDatum": None,
    }
    station.update(overrides)
    return station


def test_observation_maps_current_value_trends_and_statistics() -> None:
    """Test current value, trends and 30-day statistics."""
    series = [
        _observation("2026-07-08", 10.0),
        _observation("2026-07-15", 13.0, flag="A"),
        _observation("2026-06-20", 8.0),
        _observation("2026-07-14", 12.0),
    ]

    observation = observation_from_niwis(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        series,
    )

    assert observation.measurement_type is HydroMeasurementType.GROUNDWATER_LEVEL
    assert observation.value == pytest.approx(13.0)
    assert observation.unit == "m. ü. NHN"
    assert observation.observed_on == date(2026, 7, 15)
    assert observation.quality_flag == "A"

    assert observation.change_1d == pytest.approx(1.0)
    assert observation.change_7d == pytest.approx(3.0)

    assert observation.minimum_30d == pytest.approx(8.0)
    assert observation.maximum_30d == pytest.approx(13.0)
    assert observation.sample_count == 4


def test_observation_ignores_technical_placeholder_values() -> None:
    """Test that NIWIS placeholder values are ignored."""
    series = [
        _observation("2026-07-16", -777),
        _observation("2026-07-15", 10.0),
        _observation("2026-07-14", -888),
        _observation("2026-07-10", 8.0),
        _observation("2026-07-08", -999),
        _observation("2026-07-07", -9999),
    ]

    observation = observation_from_niwis(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        series,
    )

    assert observation.value == pytest.approx(10.0)
    assert observation.observed_on == date(2026, 7, 15)

    assert observation.minimum_30d == pytest.approx(8.0)
    assert observation.maximum_30d == pytest.approx(10.0)
    assert observation.sample_count == 2


def test_observation_uses_previous_available_value_for_date_gaps() -> None:
    """Test trends when exact comparison dates are missing."""
    series = [
        _observation("2026-07-15", 13.0),
        _observation("2026-07-13", 12.0),
        _observation("2026-07-05", 9.0),
    ]

    observation = observation_from_niwis(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        series,
    )

    # No value exists for 14 July, so 13 July is used.
    assert observation.change_1d == pytest.approx(1.0)

    # No value exists for 8 July, so 5 July is used.
    assert observation.change_7d == pytest.approx(4.0)


def test_observation_regression_real_groundwater_series() -> None:
    """Regression test using a real NIWIS groundwater series."""

    series = [
        _observation("2026-06-17", 608.18),
        _observation("2026-06-18", 608.17),
        _observation("2026-06-19", 608.17),
        _observation("2026-06-20", 608.17),
        _observation("2026-06-21", 608.16),
        _observation("2026-06-22", 608.16),
        _observation("2026-06-23", 608.15),
        _observation("2026-06-24", 608.15),
        _observation("2026-06-25", 608.15),
        _observation("2026-06-26", 608.14),
        _observation("2026-06-27", 608.14),
        _observation("2026-06-28", 608.14),
        _observation("2026-06-29", 608.13),
        _observation("2026-06-30", 608.13),
        _observation("2026-07-01", 608.12),
        _observation("2026-07-02", 608.12),
        _observation("2026-07-03", 608.12),
        _observation("2026-07-04", 608.11),
        _observation("2026-07-05", 608.11),
        _observation("2026-07-06", 608.10),
        _observation("2026-07-07", 608.10),
        _observation("2026-07-08", 608.10),
        _observation("2026-07-09", 608.09),
        _observation("2026-07-10", 608.09),
        _observation("2026-07-11", 608.09),
        _observation("2026-07-12", 608.08),
        _observation("2026-07-13", 608.08),
        _observation("2026-07-14", 608.07),
        _observation("2026-07-15", 608.07),
    ]

    observation = observation_from_niwis(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        series,
    )

    assert observation.value == pytest.approx(608.07)
    assert observation.observed_on == date(2026, 7, 15)

    # 14.07 = 608.07
    assert observation.change_1d == pytest.approx(0.0)

    # 08.07 = 608.10
    assert observation.change_7d == pytest.approx(-0.03)

    assert observation.minimum_30d == pytest.approx(608.07)
    assert observation.maximum_30d == pytest.approx(608.18)

    assert observation.sample_count == 29


def test_observation_returns_empty_result_for_empty_series() -> None:
    """Test an empty NIWIS time series."""
    observation = observation_from_niwis(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        [],
    )

    assert observation.value is None
    assert observation.unit is None
    assert observation.observed_on is None
    assert observation.change_1d is None
    assert observation.change_7d is None
    assert observation.minimum_30d is None
    assert observation.maximum_30d is None
    assert observation.sample_count == 0


def test_observation_returns_empty_result_for_only_invalid_values() -> None:
    """Test a time series containing only invalid values."""
    series = [
        _observation("2026-07-15", -777),
        _observation("2026-07-14", -888),
        _observation("2026-07-13", -999),
        _observation("2026-07-12", -9999),
        _observation("invalid-date", 10.0),
        _observation("2026-07-11", "not-a-number"),
    ]

    observation = observation_from_niwis(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        series,
    )

    assert observation.value is None
    assert observation.observed_on is None
    assert observation.change_1d is None
    assert observation.change_7d is None
    assert observation.minimum_30d is None
    assert observation.maximum_30d is None
    assert observation.sample_count == 0


def test_station_maps_extended_metadata() -> None:
    """Test mapping of extended NIWIS station metadata."""
    station = station_from_niwis(_station())

    assert station.provider == "niwis"
    assert station.station_id == "DESM_DEBY16607001"
    assert station.country_code == "DEBY"
    assert station.waterbody == "Amper"
    assert station.waterbody_code == "164"
    assert station.waterbody_position == "11.9"
    assert station.catchment_area_km2 == pytest.approx(3097)
    assert station.gauge_zero_elevation == pytest.approx(415.58)
    assert station.elevation_system == "DHHN12"
    assert station.operator == "WWA München"
    assert station.institution == "LfU BY"
    assert station.institution_url == "https://www.gkd.bayern.de/de/"
    assert station.source_url == "https://example.invalid/station"
    assert station.license_name == "cc-by/4.0"
    assert station.remarks == "Example station"
    assert station.historical_low_discharge == pytest.approx(10.7)
    assert station.historical_low_discharge_date == date(1947, 10, 3)


def test_station_maps_groundwater_specific_metadata() -> None:
    """Test mapping of groundwater-specific NIWIS metadata."""
    station = station_from_niwis(
        _station(
            messstelleNr="DEGM_DEBY83614",
            name="NBS-H/W KB 11/1",
            messgroesse=["Grundwasserstand"],
            messstellentyp="W",
            ortslage="Obersinn",
            gewaesser=None,
            gkz=None,
            lageGewaesser=None,
            ezgGroesse=None,
            hoeheGok=233.3,
            hoehePnp=None,
            teilraumName="Spessart",
            teilraumNr="6201",
            nnq=None,
            nnqDatum=None,
        )
    )

    assert station.measurement_types == (HydroMeasurementType.GROUNDWATER_LEVEL,)
    assert station.station_type == "W"
    assert station.locality == "Obersinn"
    assert station.elevation_ground == pytest.approx(233.3)
    assert station.hydrogeological_region == "Spessart"
    assert station.hydrogeological_region_code == "6201"
    assert station.historical_low_discharge is None
    assert station.historical_low_discharge_date is None


def test_station_invalid_historical_dates_are_ignored() -> None:
    """Test invalid historical NIWIS dates."""
    station = station_from_niwis(
        _station(
            nnqDatum="not-a-date",
            nnw=123.4,
            nnwDatum="also-invalid",
        )
    )

    assert station.historical_low_discharge == pytest.approx(10.7)
    assert station.historical_low_discharge_date is None
    assert station.historical_low_water_level == pytest.approx(123.4)
    assert station.historical_low_water_level_date is None


def test_low_water_class_maps_normal_value() -> None:
    """Test mapping of a normal low-water classification result."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "extrem niedrig",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == ("extremely_low", "extrem niedrig", None)


def test_low_water_class_maps_second_observed_value() -> None:
    """Test mapping of the other real-world observed category label."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "Kein Niedrigwasser",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == ("no_low_water", "Kein Niedrigwasser", None)


def test_low_water_class_maps_case_insensitively() -> None:
    """Test that label matching ignores case.

    NIWIS is inconsistent about capitalization of "kein Niedrigwasser"
    across its own endpoints (capital K in berechneEinzelwertKategorie
    samples, lowercase k in classification-boundary samples).
    """
    result = low_water_class_from_niwis(
        {
            "einzelwert": "kein niedrigwasser",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == ("no_low_water", "kein niedrigwasser", None)


def test_low_water_class_unrecognized_label_preserves_raw_value() -> None:
    """Test that an unmapped label is not discarded, only left unmapped."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "irgendwas",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == (None, "irgendwas", None)


def test_low_water_class_too_many_missing_values_without_error_message() -> None:
    """Test that hatZuvieleFehlwerte suppresses the class but preserves the raw label."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "extrem niedrig",
            "einheit": None,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": None,
        }
    )

    assert result == (None, "extrem niedrig", None)


def test_low_water_class_too_many_missing_values_with_error_message() -> None:
    """Test that hatZuvieleFehlwerte together with fehlermeldung preserves the error."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": None,
            "einheit": None,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": "Zu viele Fehlwerte im Referenzzeitraum",
        }
    )

    assert result == (None, None, "Zu viele Fehlwerte im Referenzzeitraum")


def test_low_water_class_error_message_takes_priority_over_value() -> None:
    """Test that a present fehlermeldung suppresses the mapped class but preserves the raw label."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "extrem niedrig",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": "Berechnung fehlgeschlagen",
        }
    )

    assert result == (None, "extrem niedrig", "Berechnung fehlgeschlagen")


def test_low_water_class_empty_value_is_ignored() -> None:
    """Test that an empty einzelwert string is treated as no class."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == (None, None, None)


def test_low_water_class_missing_value_key_is_ignored() -> None:
    """Test that a missing einzelwert key is treated as no class."""
    result = low_water_class_from_niwis(
        {
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == (None, None, None)


@pytest.mark.parametrize("payload", [None, [], "oops", 42])
def test_low_water_class_rejects_non_dict_input(payload: object) -> None:
    """Test that malformed non-dict responses are treated as no class."""
    assert low_water_class_from_niwis(payload) == (None, None, None)


@pytest.mark.parametrize(
    ("reference_date", "expected_index"),
    [
        # Leap year: table row 60 = Feb 29, no adjustment needed anywhere.
        (date(2024, 1, 1), 1),
        (date(2024, 2, 28), 59),
        (date(2024, 2, 29), 60),
        (date(2024, 3, 1), 61),
        (date(2024, 12, 31), 366),
        # Non-leap year: dates on/after 1 March need +1 to skip the
        # table's phantom Feb 29 row.
        (date(2025, 1, 1), 1),
        (date(2025, 2, 28), 59),
        (date(2025, 3, 1), 61),
        (date(2025, 12, 31), 366),
    ],
)
def test_day_of_year_index(reference_date: date, expected_index: int) -> None:
    """Test leap-year-aware alignment to NIWIS's fixed 366-row table."""
    assert day_of_year_index(reference_date) == expected_index


def test_static_boundaries_maps_real_fixture() -> None:
    """Test mapping of a real captured static-boundaries response."""
    data = json.loads(
        (
            INVENTORY_DIR
            / "derived_results"
            / "berechneKlassifikationsgrenzeStatisch"
            / "abfluss__abfluss_klassifikation_mit_statischen_grenzwerten.json"
        ).read_text(encoding="utf-8")
    )

    boundaries = static_low_water_boundaries_from_niwis(data)

    assert boundaries.classification_labels == (
        "extremely_low",
        "very_low",
        "low",
        "no_low_water",
    )
    assert boundaries.open_ended is True
    assert boundaries.static_thresholds == pytest.approx((20.3, 25.0, 33.4))
    assert boundaries.static_unit == "m³/s"
    assert boundaries.static_error is None
    assert boundaries.dynamic_thresholds is None


def test_static_boundaries_too_many_missing_values() -> None:
    """Test that hatZuvieleFehlwerte suppresses thresholds but keeps labels."""
    boundaries = static_low_water_boundaries_from_niwis(
        {
            "schwellenwerte": [20.3, 25.0, 33.4],
            "klassifikationen": [
                "extrem niedrig",
                "sehr niedrig",
                "niedrig",
                "kein Niedrigwasser",
            ],
            "einheit": "m³/s",
            "beidseitigOffeneSchwellenwerte": True,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": None,
        }
    )

    assert boundaries.classification_labels == (
        "extremely_low",
        "very_low",
        "low",
        "no_low_water",
    )
    assert boundaries.static_thresholds is None
    assert boundaries.static_error is None


def test_static_boundaries_error_message() -> None:
    """Test that a present fehlermeldung suppresses thresholds and is preserved."""
    boundaries = static_low_water_boundaries_from_niwis(
        {
            "schwellenwerte": [20.3, 25.0, 33.4],
            "klassifikationen": [
                "extrem niedrig",
                "sehr niedrig",
                "niedrig",
                "kein Niedrigwasser",
            ],
            "einheit": "m³/s",
            "beidseitigOffeneSchwellenwerte": True,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": "Berechnung fehlgeschlagen",
        }
    )

    assert boundaries.static_thresholds is None
    assert boundaries.static_error == "Berechnung fehlgeschlagen"


def test_static_boundaries_unrecognized_labels() -> None:
    """Test that an unexpected klassifikationen shape is rejected defensively.

    This is also the guard against the dynamic endpoint's shared, 10-class
    decile shape ever being misrouted into this classification parser.
    """
    boundaries = static_low_water_boundaries_from_niwis(
        {
            "schwellenwerte": [1.0, 2.0, 3.0],
            "klassifikationen": ["a", "b", "c", "d"],
            "einheit": "m³/s",
            "beidseitigOffeneSchwellenwerte": True,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert boundaries.classification_labels is None
    assert boundaries.static_thresholds is None
    assert boundaries.static_error == "unrecognized classification labels"


def test_static_boundaries_malformed_thresholds() -> None:
    """Test that a wrong-length schwellenwerte array is rejected."""
    boundaries = static_low_water_boundaries_from_niwis(
        {
            "schwellenwerte": [20.3, 25.0],
            "klassifikationen": [
                "extrem niedrig",
                "sehr niedrig",
                "niedrig",
                "kein Niedrigwasser",
            ],
            "einheit": "m³/s",
            "beidseitigOffeneSchwellenwerte": True,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert boundaries.classification_labels is not None
    assert boundaries.static_thresholds is None
    assert boundaries.static_error == "malformed schwellenwerte"


@pytest.mark.parametrize("payload", [None, [], "oops", 42])
def test_static_boundaries_rejects_non_dict_input(payload: object) -> None:
    """Test that malformed non-dict responses map to an empty result."""
    boundaries = static_low_water_boundaries_from_niwis(payload)
    assert boundaries.classification_labels is None
    assert boundaries.static_thresholds is None
    assert boundaries.static_error is None


def test_dynamic_boundaries_maps_real_fixture() -> None:
    """Test mapping of a real captured dynamic-boundaries response."""
    data = json.loads(
        (
            INVENTORY_DIR
            / "derived_results"
            / "berechneKlassifikationsgrenzeDynamisch"
            / "abfluss__abfluss_klassifikation_mit_variablen_grenzwerten.json"
        ).read_text(encoding="utf-8")
    )
    reference_date = date(2026, 1, 15)
    expected_row = data["schwellenwerteProTag"][day_of_year_index(reference_date) - 1]

    boundaries = dynamic_low_water_boundaries_from_niwis(data, reference_date)

    assert boundaries.classification_labels == (
        "extremely_low",
        "very_low",
        "low",
        "no_low_water",
    )
    assert boundaries.dynamic_thresholds == pytest.approx(tuple(expected_row))
    assert boundaries.dynamic_unit == "m³/s"
    assert boundaries.dynamic_reference_date == reference_date
    assert boundaries.dynamic_error is None
    assert boundaries.static_thresholds is None


def test_dynamic_boundaries_missing_row_table() -> None:
    """Test that a wrong-length schwellenwerteProTag is rejected."""
    boundaries = dynamic_low_water_boundaries_from_niwis(
        {
            "schwellenwerteProTag": [[1.0, 2.0, 3.0]] * 10,
            "klassifikationen": [
                "extrem niedrig",
                "sehr niedrig",
                "niedrig",
                "kein Niedrigwasser",
            ],
            "einheit": "m³/s",
            "beidseitigOffeneSchwellenwerte": True,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        },
        date(2026, 1, 15),
    )

    assert boundaries.classification_labels is not None
    assert boundaries.dynamic_thresholds is None
    assert boundaries.dynamic_error == "missing per-day threshold row"


def test_dynamic_boundaries_malformed_row() -> None:
    """Test that a row with the wrong number of thresholds is rejected."""
    boundaries = dynamic_low_water_boundaries_from_niwis(
        {
            "schwellenwerteProTag": [[1.0, 2.0]] * 366,
            "klassifikationen": [
                "extrem niedrig",
                "sehr niedrig",
                "niedrig",
                "kein Niedrigwasser",
            ],
            "einheit": "m³/s",
            "beidseitigOffeneSchwellenwerte": True,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        },
        date(2026, 1, 15),
    )

    assert boundaries.dynamic_thresholds is None
    assert boundaries.dynamic_error == "malformed schwellenwerteProTag row"


def test_dynamic_boundaries_too_many_missing_values() -> None:
    """Test that hatZuvieleFehlwerte suppresses thresholds but keeps labels."""
    boundaries = dynamic_low_water_boundaries_from_niwis(
        {
            "schwellenwerteProTag": [[1.0, 2.0, 3.0]] * 366,
            "klassifikationen": [
                "extrem niedrig",
                "sehr niedrig",
                "niedrig",
                "kein Niedrigwasser",
            ],
            "einheit": "m³/s",
            "beidseitigOffeneSchwellenwerte": True,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": None,
        },
        date(2026, 1, 15),
    )

    assert boundaries.classification_labels is not None
    assert boundaries.dynamic_thresholds is None
    assert boundaries.dynamic_error is None


@pytest.mark.parametrize("payload", [None, [], "oops", 42])
def test_dynamic_boundaries_rejects_non_dict_input(payload: object) -> None:
    """Test that malformed non-dict responses map to an empty result."""
    boundaries = dynamic_low_water_boundaries_from_niwis(payload, date(2026, 1, 15))
    assert boundaries.classification_labels is None
    assert boundaries.dynamic_thresholds is None
    assert boundaries.dynamic_error is None


def test_official_development_7d_maps_normal_value() -> None:
    """Test mapping of the only real-world observed development value."""
    result = official_development_7d_from_niwis(
        {
            "einzelwert": "gleichbleibend",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == ("gleichbleibend", "gleichbleibend", None)


def test_official_development_7d_too_many_missing_values_without_error_message() -> None:
    """Test that hatZuvieleFehlwerte suppresses the value but preserves the raw label."""
    result = official_development_7d_from_niwis(
        {
            "einzelwert": "gleichbleibend",
            "einheit": None,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": None,
        }
    )

    assert result == (None, "gleichbleibend", None)


def test_official_development_7d_too_many_missing_values_with_error_message() -> None:
    """Test that hatZuvieleFehlwerte together with fehlermeldung preserves the error."""
    result = official_development_7d_from_niwis(
        {
            "einzelwert": None,
            "einheit": None,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": "Zu viele Fehlwerte im Referenzzeitraum",
        }
    )

    assert result == (None, None, "Zu viele Fehlwerte im Referenzzeitraum")


def test_official_development_7d_error_message_takes_priority_over_value() -> None:
    """Test that a present fehlermeldung suppresses the value but preserves the raw label."""
    result = official_development_7d_from_niwis(
        {
            "einzelwert": "gleichbleibend",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": "Berechnung fehlgeschlagen",
        }
    )

    assert result == (None, "gleichbleibend", "Berechnung fehlgeschlagen")


def test_official_development_7d_empty_value_is_ignored() -> None:
    """Test that an empty einzelwert string is treated as no value."""
    result = official_development_7d_from_niwis(
        {
            "einzelwert": "",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == (None, None, None)


def test_official_development_7d_missing_value_key_is_ignored() -> None:
    """Test that a missing einzelwert key is treated as no value."""
    result = official_development_7d_from_niwis(
        {
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == (None, None, None)


@pytest.mark.parametrize("payload", [None, [], "oops", 42])
def test_official_development_7d_rejects_non_dict_input(payload: object) -> None:
    """Test that malformed non-dict responses are treated as no value."""
    assert official_development_7d_from_niwis(payload) == (None, None, None)


def test_as_float_rejects_nan_string() -> None:
    """Test that the literal NIWIS 'NaN' placeholder is rejected."""
    assert as_float("NaN") is None


def test_as_float_rejects_float_nan() -> None:
    """Test that a real NaN float is rejected, not silently passed through."""
    assert as_float(float("nan")) is None


def test_historical_statistic_maps_normal_value() -> None:
    """Test mapping of a normal numeric historical-statistic result."""
    stat = historical_statistic_from_niwis(
        {
            "einzelwert": 46.41388,
            "einheit": "m³/s",
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert stat.value == pytest.approx(46.41388)
    assert stat.unit == "m³/s"
    assert stat.error is None


def test_historical_statistic_too_many_missing_values_without_error_message() -> None:
    """Test that hatZuvieleFehlwerte suppresses the value."""
    stat = historical_statistic_from_niwis(
        {
            "einzelwert": 46.41388,
            "einheit": "m³/s",
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": None,
        }
    )

    assert stat.value is None
    assert stat.unit == "m³/s"
    assert stat.error is None


def test_historical_statistic_too_many_missing_values_with_error_message() -> None:
    """Test that hatZuvieleFehlwerte together with fehlermeldung preserves the error."""
    stat = historical_statistic_from_niwis(
        {
            "einzelwert": None,
            "einheit": None,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": "Zu viele Fehlwerte im Referenzzeitraum",
        }
    )

    assert stat.value is None
    assert stat.error == "Zu viele Fehlwerte im Referenzzeitraum"


def test_historical_statistic_error_message_takes_priority_over_value() -> None:
    """Test that a present fehlermeldung suppresses an also-present einzelwert."""
    stat = historical_statistic_from_niwis(
        {
            "einzelwert": 46.41388,
            "einheit": "m³/s",
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": "Berechnung fehlgeschlagen",
        }
    )

    assert stat.value is None
    assert stat.error == "Berechnung fehlgeschlagen"


def test_historical_statistic_rejects_nan_value() -> None:
    """Test the real-world NIWIS shape where einzelwert is the string 'NaN'.

    Based on niwis_inventory/derived_results/berechneEinzelwertNummer/
    wasserstand__tage_unter_glwrnwbwu_aktueller_tag.json.
    """
    stat = historical_statistic_from_niwis(
        {
            "einzelwert": "NaN",
            "einheit": None,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": None,
        }
    )

    assert stat.value is None


@pytest.mark.parametrize("payload", [None, [], "oops", 42])
def test_historical_statistic_rejects_non_dict_input(payload: object) -> None:
    """Test that malformed non-dict responses map to an empty result."""
    stat = historical_statistic_from_niwis(payload)
    assert stat.value is None
    assert stat.unit is None
    assert stat.error is None


_DECILE_LABELS = (
    "0-10%", "10-20%", "20-30%", "30-40%", "40-50%",
    "50-60%", "60-70%", "70-80%", "80-90%", "90-100%",
)


def _decile_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS deciles response."""
    response: dict[str, object] = {
        "schwellenwerteProTag": [list(range(11))] * 366,
        "klassifikationen": list(_DECILE_LABELS),
        "einheit": "m³/s",
        "beidseitigOffeneSchwellenwerte": False,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def test_deciles_maps_real_discharge_fixture() -> None:
    """Test mapping of a real captured discharge deciles response."""
    data = json.loads(
        (
            INVENTORY_DIR
            / "derived_results"
            / "berechneKlassifikationsgrenzeDynamisch"
            / "abfluss__abfluss_dezile_tageweise.json"
        ).read_text(encoding="utf-8")
    )
    reference_date = date(2026, 1, 15)
    expected_row = data["schwellenwerteProTag"][day_of_year_index(reference_date) - 1]

    deciles = deciles_from_niwis(data, reference_date)

    assert deciles.classification_labels == _DECILE_LABELS
    assert len(deciles.thresholds) == 11
    assert deciles.thresholds == pytest.approx(tuple(expected_row))
    assert deciles.unit == "m³/s"
    assert deciles.reference_date == reference_date
    assert deciles.error is None


def test_deciles_maps_real_water_level_fixture() -> None:
    """Test mapping of a real captured water-level deciles response."""
    data = json.loads(
        (
            INVENTORY_DIR
            / "derived_results"
            / "berechneKlassifikationsgrenzeDynamisch"
            / "wasserstand__wasserstand_dezile_tageweise.json"
        ).read_text(encoding="utf-8")
    )
    reference_date = date(2026, 1, 15)

    deciles = deciles_from_niwis(data, reference_date)

    assert deciles.classification_labels == _DECILE_LABELS
    assert len(deciles.thresholds) == 11
    assert deciles.unit == "cm"
    assert deciles.error is None


def test_deciles_missing_row_table() -> None:
    """Test that a wrong-length schwellenwerteProTag is rejected."""
    deciles = deciles_from_niwis(
        _decile_response(schwellenwerteProTag=[list(range(11))] * 10),
        date(2026, 1, 15),
    )

    assert deciles.classification_labels == _DECILE_LABELS
    assert deciles.thresholds is None
    assert deciles.error == "missing per-day threshold row"


def test_deciles_malformed_row() -> None:
    """Test that a row without exactly 11 values is rejected.

    Direct regression guard for the len(labels) + 1 formula: naively
    reusing the low-water boundaries' len(labels) - 1 formula (9, not 11)
    would silently reject every real decile response.
    """
    deciles = deciles_from_niwis(
        _decile_response(schwellenwerteProTag=[[1.0, 2.0, 3.0]] * 366),
        date(2026, 1, 15),
    )

    assert deciles.classification_labels == _DECILE_LABELS
    assert deciles.thresholds is None
    assert deciles.error == "malformed schwellenwerteProTag row"


def test_deciles_too_many_missing_values() -> None:
    """Test that hatZuvieleFehlwerte suppresses thresholds but keeps labels."""
    deciles = deciles_from_niwis(
        _decile_response(hatZuvieleFehlwerte=True),
        date(2026, 1, 15),
    )

    assert deciles.classification_labels == _DECILE_LABELS
    assert deciles.thresholds is None
    assert deciles.error is None


def test_deciles_unrecognized_labels() -> None:
    """Test that the low-water 4-class labels are rejected here.

    Guards against the shared/overloaded berechneKlassifikationsgrenzeDynamisch
    endpoint ever returning the low-water boundaries' shape here by mistake.
    """
    deciles = deciles_from_niwis(
        _decile_response(
            klassifikationen=["extrem niedrig", "sehr niedrig", "niedrig", "kein Niedrigwasser"]
        ),
        date(2026, 1, 15),
    )

    assert deciles.classification_labels is None
    assert deciles.thresholds is None
    assert deciles.error == "unrecognized classification labels"


@pytest.mark.parametrize("payload", [None, [], "oops", 42])
def test_deciles_rejects_non_dict_input(payload: object) -> None:
    """Test that malformed non-dict responses map to an empty result."""
    deciles = deciles_from_niwis(payload, date(2026, 1, 15))
    assert deciles.classification_labels is None
    assert deciles.thresholds is None
    assert deciles.error is None

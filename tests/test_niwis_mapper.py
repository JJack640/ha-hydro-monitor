"""Tests for the NIWIS data mapper."""

from datetime import date

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType
from custom_components.hydro_monitor.providers.niwis.mapper import (
    low_water_class_from_niwis,
    observation_from_niwis,
    station_from_niwis,
)


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

    assert result == ("extrem niedrig", None)


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

    assert result == ("Kein Niedrigwasser", None)


def test_low_water_class_too_many_missing_values_without_error_message() -> None:
    """Test that hatZuvieleFehlwerte alone suppresses the class."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "extrem niedrig",
            "einheit": None,
            "hatZuvieleFehlwerte": True,
            "fehlermeldung": None,
        }
    )

    assert result == (None, None)


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

    assert result == (None, "Zu viele Fehlwerte im Referenzzeitraum")


def test_low_water_class_error_message_takes_priority_over_value() -> None:
    """Test that a present fehlermeldung suppresses an also-present einzelwert."""
    result = low_water_class_from_niwis(
        {
            "einzelwert": "extrem niedrig",
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": "Berechnung fehlgeschlagen",
        }
    )

    assert result == (None, "Berechnung fehlgeschlagen")


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

    assert result == (None, None)


def test_low_water_class_missing_value_key_is_ignored() -> None:
    """Test that a missing einzelwert key is treated as no class."""
    result = low_water_class_from_niwis(
        {
            "einheit": None,
            "hatZuvieleFehlwerte": False,
            "fehlermeldung": None,
        }
    )

    assert result == (None, None)


@pytest.mark.parametrize("payload", [None, [], "oops", 42])
def test_low_water_class_rejects_non_dict_input(payload: object) -> None:
    """Test that malformed non-dict responses are treated as no class."""
    assert low_water_class_from_niwis(payload) == (None, None)

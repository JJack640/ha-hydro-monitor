"""Tests for the NIWIS data mapper."""

from datetime import date

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType
from custom_components.hydro_monitor.providers.niwis.mapper import (
    observation_from_niwis,
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

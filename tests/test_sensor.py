"""Tests for Hydro Monitor sensor helpers and descriptions."""

from datetime import UTC, date, datetime

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from custom_components.hydro_monitor import sensor as sensor_module
from custom_components.hydro_monitor.models import (
    HydroMeasurementType,
    HydroObservation,
)
from custom_components.hydro_monitor.sensor import (
    SENSOR_DESCRIPTIONS,
    TREND_STATE_OPTIONS,
    _measurement_age_hours,
    _measurement_datetime,
    _trend_icon,
    _trend_state,
)


def _observation(
    *,
    value: float | None = 608.07,
    observed_on: date | datetime | None = date(2026, 7, 15),
    change_1d: float | None = 0.0,
    change_7d: float | None = -0.02,
    minimum_30d: float | None = 608.07,
    maximum_30d: float | None = 608.18,
) -> HydroObservation:
    """Create a Hydro Monitor observation for sensor tests."""
    return HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=value,
        unit="m. ü. NHN",
        observed_on=observed_on,
        change_1d=change_1d,
        change_7d=change_7d,
        minimum_30d=minimum_30d,
        maximum_30d=maximum_30d,
        sample_count=29,
    )


def _description(key: str):
    """Return one sensor description by key."""
    return next(
        description for description in SENSOR_DESCRIPTIONS if description.key == key
    )


@pytest.mark.parametrize(
    ("change_mm", "expected_icon"),
    [
        (None, "mdi:trending-neutral"),
        (0, "mdi:trending-neutral"),
        (1, "mdi:trending-neutral"),
        (2, "mdi:arrow-up-thin"),
        (9, "mdi:arrow-up-thin"),
        (10, "mdi:arrow-up"),
        (24, "mdi:arrow-up"),
        (25, "mdi:arrow-up-bold"),
        (-2, "mdi:arrow-down-thin"),
        (-9, "mdi:arrow-down-thin"),
        (-10, "mdi:arrow-down"),
        (-24, "mdi:arrow-down"),
        (-25, "mdi:arrow-down-bold"),
    ],
)
def test_trend_icon(
    change_mm: float | int | None,
    expected_icon: str,
) -> None:
    """Test trend icons for direction and strength."""
    assert _trend_icon(change_mm) == expected_icon


@pytest.mark.parametrize(
    ("change_7d", "expected_state"),
    [
        (None, None),
        (0.030, "strong_rising"),
        (0.025, "strong_rising"),
        (0.010, "rising"),
        (0.002, "rising"),
        (0.001, "stable"),
        (0.0, "stable"),
        (-0.001, "stable"),
        (-0.002, "falling"),
        (-0.020, "falling"),
        (-0.025, "strong_falling"),
        (-0.030, "strong_falling"),
    ],
)
def test_trend_state(
    change_7d: float | None,
    expected_state: str | None,
) -> None:
    """Test categorized seven-day trend states."""
    observation = _observation(change_7d=change_7d)

    assert _trend_state(observation) == expected_state


def test_trend_state_options() -> None:
    """Test the supported enum options and their order."""
    assert TREND_STATE_OPTIONS == [
        "strong_rising",
        "rising",
        "stable",
        "falling",
        "strong_falling",
    ]


def test_trend_descriptions_convert_metres_to_millimetres() -> None:
    """Test conversion of trend values from metres to millimetres."""
    observation = _observation(
        change_1d=0.003,
        change_7d=-0.021,
    )

    trend_1d = _description("change_1d")
    trend_7d = _description("change_7d")

    assert trend_1d.value_fn(observation) == 3
    assert trend_7d.value_fn(observation) == -21

    assert trend_1d.unit_fn(observation) == "mm"
    assert trend_7d.unit_fn(observation) == "mm"

    assert trend_1d.state_class is SensorStateClass.MEASUREMENT
    assert trend_7d.state_class is SensorStateClass.MEASUREMENT


def test_trend_descriptions_return_none_without_values() -> None:
    """Test unavailable trend values."""
    observation = _observation(
        change_1d=None,
        change_7d=None,
    )

    assert _description("change_1d").value_fn(observation) is None
    assert _description("change_7d").value_fn(observation) is None


def test_trend_state_description() -> None:
    """Test enum metadata for the trend-state sensor."""
    description = _description("trend_state")

    assert description.translation_key == "water_level_trend"
    assert description.device_class is SensorDeviceClass.ENUM
    assert description.options == TREND_STATE_OPTIONS
    assert description.unit_fn(_observation()) is None


def test_statistics_descriptions() -> None:
    """Test 30-day high and low sensor descriptions."""
    observation = _observation()

    high = _description("maximum_30d")
    low = _description("minimum_30d")

    assert high.translation_key == "high_30_days"
    assert low.translation_key == "low_30_days"

    assert high.value_fn(observation) == pytest.approx(608.18)
    assert low.value_fn(observation) == pytest.approx(608.07)

    assert high.unit_fn(observation) == "m. ü. NHN"
    assert low.unit_fn(observation) == "m. ü. NHN"


def test_measurement_datetime_from_date() -> None:
    """Test conversion of a date into an aware UTC datetime."""
    observation = _observation(
        observed_on=date(2026, 7, 15),
    )

    assert _measurement_datetime(observation) == datetime(
        2026,
        7,
        15,
        0,
        0,
        tzinfo=UTC,
    )


def test_measurement_datetime_normalizes_datetime_to_utc() -> None:
    """Test normalization of a naive datetime to UTC."""
    observation = _observation(
        observed_on=datetime(2026, 7, 15, 12, 30),
    )

    assert _measurement_datetime(observation) == datetime(
        2026,
        7,
        15,
        12,
        30,
        tzinfo=UTC,
    )


def test_measurement_datetime_returns_none_without_date() -> None:
    """Test a missing observation date."""
    assert _measurement_datetime(_observation(observed_on=None)) is None


def test_measurement_age_hours(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test measurement age calculation."""
    monkeypatch.setattr(
        sensor_module.dt_util,
        "utcnow",
        lambda: datetime(
            2026,
            7,
            16,
            12,
            30,
            tzinfo=UTC,
        ),
    )

    observation = _observation(
        observed_on=datetime(
            2026,
            7,
            15,
            12,
            0,
            tzinfo=UTC,
        ),
    )

    assert _measurement_age_hours(observation) == 24.5


def test_diagnostic_sensor_descriptions() -> None:
    """Test diagnostic metadata for timestamp and age sensors."""
    last_measurement = _description("last_measurement")
    measurement_age = _description("measurement_age")

    assert last_measurement.translation_key == "last_measurement"
    assert last_measurement.device_class is SensorDeviceClass.TIMESTAMP
    assert last_measurement.entity_category is EntityCategory.DIAGNOSTIC

    assert measurement_age.translation_key == "measurement_age"
    assert measurement_age.entity_category is EntityCategory.DIAGNOSTIC
    assert measurement_age.native_unit_of_measurement == UnitOfTime.HOURS
    assert measurement_age.state_class is SensorStateClass.MEASUREMENT
    assert measurement_age.suggested_display_precision == 1


def test_all_non_primary_sensors_have_translation_keys() -> None:
    """Test that visible non-primary names come from translations."""
    for description in SENSOR_DESCRIPTIONS:
        if description.is_primary:
            continue

        assert description.translation_key is not None
        assert description.name is None

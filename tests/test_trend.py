"""Tests for trend values, icons and states."""

import json
from datetime import date
from pathlib import Path

import pytest

from custom_components.hydro_monitor.models import (
    HydroMeasurementType,
    HydroObservation,
)
from custom_components.hydro_monitor.providers.niwis.mapper import (
    observation_from_niwis,
)
from custom_components.hydro_monitor.trend import (
    trend_icon,
    trend_state,
    trend_unit,
    trend_value,
)

INVENTORY_DIR = Path(__file__).resolve().parent.parent / "niwis_inventory"


def _observation(
    measurement_type: HydroMeasurementType,
    *,
    value: float | None,
    unit: str | None,
    change_1d: float | None = None,
    change_7d: float | None = None,
) -> HydroObservation:
    """Create an observation carrying only what trends need."""
    return HydroObservation(
        measurement_type,
        value,
        unit,
        date(2026, 10, 23),
        change_1d=change_1d,
        change_7d=change_7d,
    )


def _groundwater(change_7d: float | None) -> HydroObservation:
    return _observation(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        change_7d=change_7d,
    )


def _water_level(change_7d: float | None) -> HydroObservation:
    return _observation(
        HydroMeasurementType.WATER_LEVEL,
        value=40.0,
        unit="cm",
        change_7d=change_7d,
    )


def _discharge(change_7d: float | None, value: float | None = 10.0) -> HydroObservation:
    return _observation(
        HydroMeasurementType.DISCHARGE,
        value=value,
        unit="m³/s",
        change_7d=change_7d,
    )


@pytest.mark.parametrize(
    ("change_m", "expected_state"),
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
def test_groundwater_trend_state_is_unchanged(
    change_m: float | None,
    expected_state: str | None,
) -> None:
    """Test groundwater keeps the thresholds it always had (metres)."""
    assert trend_state(_groundwater(change_m)) == expected_state


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
def test_groundwater_trend_icon_is_unchanged(
    change_mm: int | None,
    expected_icon: str,
) -> None:
    """Test groundwater icons for direction and strength (millimetres)."""
    change_m = None if change_mm is None else change_mm / 1000

    assert trend_icon(_groundwater(change_m), change_m) == expected_icon


def test_groundwater_trend_stays_in_millimetres() -> None:
    """Test groundwater trends are still reported in whole millimetres."""
    observation = _groundwater(-0.021)

    assert trend_unit(observation) == "mm"
    assert trend_value(observation, -0.021) == -21
    assert trend_value(observation, 0.003) == 3
    assert trend_value(observation, None) is None


@pytest.mark.parametrize(
    ("change_cm", "expected_state"),
    [
        (30.0, "strong_rising"),
        (25.0, "strong_rising"),
        (5.0, "rising"),
        (1.0, "rising"),
        (0.0, "stable"),
        (-1.0, "falling"),
        (-24.0, "falling"),
        (-25.0, "strong_falling"),
    ],
)
def test_water_level_is_judged_in_centimetres(
    change_cm: float,
    expected_state: str,
) -> None:
    """Test a water level change in cm is not mistaken for metres."""
    assert trend_state(_water_level(change_cm)) == expected_state


def test_water_level_icon_steps() -> None:
    """Test the icon strength steps for a water level in centimetres."""
    observation = _water_level(0.0)

    assert trend_icon(observation, 0.5) == "mdi:trending-neutral"
    assert trend_icon(observation, 1.0) == "mdi:arrow-up-thin"
    assert trend_icon(observation, 5.0) == "mdi:arrow-up"
    assert trend_icon(observation, 25.0) == "mdi:arrow-up-bold"
    assert trend_icon(observation, -25.0) == "mdi:arrow-down-bold"


def test_water_level_trend_keeps_its_own_unit() -> None:
    """Test the water level trend is reported in cm, not millimetres."""
    observation = _water_level(0.0)

    assert trend_unit(observation) == "cm"
    assert trend_value(observation, 12.0) == 12.0
    assert trend_value(observation, 0.30000000000000004) == 0.3


def test_water_level_in_metres_is_converted() -> None:
    """Test a provider reporting metres is judged on the same scale as cm."""
    observation = _observation(
        HydroMeasurementType.WATER_LEVEL,
        value=1.4,
        unit="m",
        change_7d=0.25,
    )

    assert trend_state(observation) == "strong_rising"


@pytest.mark.parametrize(
    ("value", "change_7d", "expected_state"),
    [
        # Percent of the earlier value (value - change).
        (15.3, -1.6, "falling"),  # about -9.5 %
        (10.0, -4.0, "strong_falling"),  # about -28.6 %
        (10.0, 0.19, "stable"),  # about 1.9 %
        (10.0, 0.2, "rising"),  # about 2.0 %
        (12.5, 2.5, "strong_rising"),  # exactly +25 %
        (10.0, 0.0, "stable"),
    ],
)
def test_discharge_is_judged_relative_to_its_earlier_value(
    value: float,
    change_7d: float,
    expected_state: str,
) -> None:
    """Test discharge uses a relative scale, so big and small rivers compare."""
    assert trend_state(_discharge(change_7d, value=value)) == expected_state


def test_discharge_scale_is_independent_of_river_size() -> None:
    """Test the same relative change gives the same state at any flow."""
    brook = _discharge(0.011, value=0.11)  # +11 %
    river = _discharge(55.0, value=555.0)  # about +11 %

    assert trend_state(brook) == trend_state(river) == "rising"
    assert trend_icon(brook, 0.011) == trend_icon(river, 55.0) == "mdi:arrow-up"


def test_discharge_trend_keeps_its_own_unit() -> None:
    """Test discharge is no longer shown as millimetres."""
    observation = _discharge(-1.6, value=15.3)

    assert trend_unit(observation) == "m³/s"
    assert trend_value(observation, -1.5999999999999979) == -1.6


def test_spring_discharge_is_relative_too() -> None:
    """Test spring discharge in l/s uses the relative scale."""
    observation = _observation(
        HydroMeasurementType.SPRING_DISCHARGE,
        value=1.07,
        unit="l/s",
        change_7d=0.01,
    )

    assert trend_state(observation) == "stable"  # about 0.9 %
    assert trend_unit(observation) == "l/s"


def test_flow_starting_from_nothing_is_a_strong_rise() -> None:
    """Test a rise from zero flow does not divide by zero."""
    observation = _discharge(0.5, value=0.5)

    assert trend_state(observation) == "strong_rising"
    assert trend_icon(observation, 0.5) == "mdi:arrow-up-bold"


def test_unchanged_zero_flow_is_stable() -> None:
    """Test a dry spring that stays dry is stable."""
    observation = _discharge(0.0, value=0.0)

    assert trend_state(observation) == "stable"
    assert trend_icon(observation, 0.0) == "mdi:trending-neutral"


def test_discharge_without_value_has_no_trend_state() -> None:
    """Test a relative trend needs the current value."""
    assert trend_state(_discharge(1.0, value=None)) is None
    assert trend_icon(_discharge(1.0, value=None), 1.0) == "mdi:trending-neutral"


@pytest.mark.parametrize(
    ("measurement_type", "expected_unit", "expected_value"),
    [
        (HydroMeasurementType.DISCHARGE, "m³/s", -1.6),
        (HydroMeasurementType.WATER_LEVEL, "cm", 0.0),
        (HydroMeasurementType.GROUNDWATER_LEVEL, "mm", 0),
        (HydroMeasurementType.SPRING_DISCHARGE, "l/s", 0.01),
    ],
)
def test_real_niwis_series_give_plausible_trends(
    measurement_type: HydroMeasurementType,
    expected_unit: str,
    expected_value: float,
) -> None:
    """Regression with real NIWIS captures.

    Before the fix the discharge fall of 1.6 m³/s was shown as -1600 mm.
    """
    path = sorted((INVENTORY_DIR / "series" / measurement_type.value).glob("*.json"))[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    series = data if isinstance(data, list) else next(
        value for value in data.values() if isinstance(value, list)
    )

    observation = observation_from_niwis(measurement_type, series)

    assert trend_unit(observation) == expected_unit
    assert trend_value(observation, observation.change_7d) == pytest.approx(
        expected_value
    )

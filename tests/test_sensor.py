"""Tests for Hydro Monitor sensor helpers and descriptions."""

from datetime import UTC, date, datetime

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from custom_components.hydro_monitor import sensor as sensor_module
from custom_components.hydro_monitor.models import (
    HydroCalendarDayValue,
    HydroDatedExtreme,
    HydroDeciles,
    HydroDerivedValue,
    HydroLowWaterBoundaries,
    HydroMeasurementType,
    HydroObservation,
)
from custom_components.hydro_monitor.providers.niwis.const import (
    LOW_WATER_CLASS_KEYS,
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
    low_water_class: str | None = None,
    low_water_class_error: str | None = None,
    boundaries: HydroLowWaterBoundaries | None = None,
    deciles: HydroDeciles | None = None,
    official_development_7d: str | None = None,
    official_development_7d_raw: str | None = None,
    official_development_7d_error: str | None = None,
    mq: HydroDerivedValue | None = None,
    mnq: HydroDerivedValue | None = None,
    nm7q: HydroDerivedValue | None = None,
    nm30q: HydroDerivedValue | None = None,
    mw: HydroDerivedValue | None = None,
    mnw: HydroDerivedValue | None = None,
    nq: HydroDerivedValue | None = None,
    median_q: HydroDerivedValue | None = None,
    nw: HydroDerivedValue | None = None,
    median_w: HydroDerivedValue | None = None,
    nm7q_dated: HydroDatedExtreme | None = None,
    nm30q_dated: HydroDatedExtreme | None = None,
    min_q_calendar_day: HydroCalendarDayValue | None = None,
    median_q_calendar_day: HydroCalendarDayValue | None = None,
    max_q_calendar_day: HydroCalendarDayValue | None = None,
    median_w_calendar_day: HydroCalendarDayValue | None = None,
    sum_d: HydroDerivedValue | None = None,
    sum_v: HydroDerivedValue | None = None,
    below_glw: str | None = None,
    below_glw_raw: str | None = None,
    below_glw_error: str | None = None,
    days_below_glw: HydroDerivedValue | None = None,
    depth_below_ground: HydroDerivedValue | None = None,
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
        low_water_class=low_water_class,
        low_water_class_error=low_water_class_error,
        boundaries=boundaries,
        deciles=deciles,
        official_development_7d=official_development_7d,
        official_development_7d_raw=official_development_7d_raw,
        official_development_7d_error=official_development_7d_error,
        mq=mq,
        mnq=mnq,
        nm7q=nm7q,
        nm30q=nm30q,
        mw=mw,
        mnw=mnw,
        nq=nq,
        median_q=median_q,
        nw=nw,
        median_w=median_w,
        nm7q_dated=nm7q_dated,
        nm30q_dated=nm30q_dated,
        min_q_calendar_day=min_q_calendar_day,
        median_q_calendar_day=median_q_calendar_day,
        max_q_calendar_day=max_q_calendar_day,
        median_w_calendar_day=median_w_calendar_day,
        sum_d=sum_d,
        sum_v=sum_v,
        below_glw=below_glw,
        below_glw_raw=below_glw_raw,
        below_glw_error=below_glw_error,
        days_below_glw=days_below_glw,
        depth_below_ground=depth_below_ground,
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


def test_low_water_class_description() -> None:
    """Test the official low-water classification sensor description.

    The full domain of NIWIS category labels was confirmed (via the
    classification-boundary endpoints) to be a fixed 4-value scheme, so
    this is a proper SensorDeviceClass.ENUM sensor with a stable options
    list, mirroring the water_level_trend pattern.
    """
    description = _description("low_water_class")

    assert description.translation_key == "low_water_class"
    assert description.device_class is SensorDeviceClass.ENUM
    assert description.options == list(LOW_WATER_CLASS_KEYS)
    assert description.entity_category is None

    observation = _observation(low_water_class="extremely_low")
    assert description.value_fn(observation) == "extremely_low"
    assert description.unit_fn(observation) is None
    assert description.value_fn(_observation()) is None


def test_official_development_7d_description() -> None:
    """Test the official 7-day development sensor description.

    Unlike low_water_class, this stays a plain string sensor: NIWIS's
    development-direction vocabulary is unconfirmed (only "gleichbleibend"
    observed), so no device_class/options are declared yet.
    """
    description = _description("official_development_7d")

    assert description.translation_key == "official_development_7d"
    assert description.device_class is None
    assert description.options is None
    assert description.entity_category is None
    assert description.entity_registry_enabled_default is True

    observation = _observation(official_development_7d="gleichbleibend")
    assert description.value_fn(observation) == "gleichbleibend"
    assert description.unit_fn(observation) is None
    assert description.value_fn(_observation()) is None


@pytest.mark.parametrize(
    ("key", "index"),
    [
        ("boundary_static_extremely_low", 0),
        ("boundary_static_very_low", 1),
        ("boundary_static_low", 2),
    ],
)
def test_static_boundary_descriptions(key: str, index: int) -> None:
    """Test the static low-water boundary sensor descriptions."""
    description = _description(key)

    assert description.translation_key == key
    assert description.entity_registry_enabled_default is False
    assert description.entity_category is None

    boundaries = HydroLowWaterBoundaries(
        static_thresholds=(20.3, 25.0, 33.4),
        static_unit="m³/s",
    )
    observation = _observation(boundaries=boundaries)
    assert description.value_fn(observation) == pytest.approx(
        (20.3, 25.0, 33.4)[index]
    )
    assert description.unit_fn(observation) == "m³/s"

    # None-safe when boundaries are missing entirely or lack thresholds.
    assert description.value_fn(_observation()) is None
    assert description.value_fn(_observation(boundaries=HydroLowWaterBoundaries())) is None
    assert description.unit_fn(_observation()) is None


@pytest.mark.parametrize(
    ("key", "index"),
    [
        ("boundary_dynamic_extremely_low", 0),
        ("boundary_dynamic_very_low", 1),
        ("boundary_dynamic_low", 2),
    ],
)
def test_dynamic_boundary_descriptions(key: str, index: int) -> None:
    """Test the dynamic low-water boundary sensor descriptions."""
    description = _description(key)

    assert description.translation_key == key
    assert description.entity_registry_enabled_default is False
    assert description.entity_category is None

    boundaries = HydroLowWaterBoundaries(
        dynamic_thresholds=(24.3, 26.0, 33.6),
        dynamic_unit="m³/s",
    )
    observation = _observation(boundaries=boundaries)
    assert description.value_fn(observation) == pytest.approx(
        (24.3, 26.0, 33.6)[index]
    )
    assert description.unit_fn(observation) == "m³/s"

    # None-safe when boundaries are missing entirely or lack thresholds.
    assert description.value_fn(_observation()) is None
    assert description.value_fn(_observation(boundaries=HydroLowWaterBoundaries())) is None
    assert description.unit_fn(_observation()) is None


@pytest.mark.parametrize(
    ("key", "index"),
    [
        ("decile_p0", 0),
        ("decile_p10", 1),
        ("decile_p20", 2),
        ("decile_p30", 3),
        ("decile_p40", 4),
        ("decile_p50", 5),
        ("decile_p60", 6),
        ("decile_p70", 7),
        ("decile_p80", 8),
        ("decile_p90", 9),
        ("decile_p100", 10),
    ],
)
def test_decile_descriptions(key: str, index: int) -> None:
    """Test the official NIWIS decile sensor descriptions."""
    description = _description(key)

    assert description.translation_key == key
    assert description.entity_registry_enabled_default is False
    assert description.entity_category is None
    assert description.state_class == SensorStateClass.MEASUREMENT

    thresholds = (10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0)
    deciles = HydroDeciles(thresholds=thresholds, unit="m³/s")
    observation = _observation(deciles=deciles)
    assert description.value_fn(observation) == pytest.approx(thresholds[index])
    assert description.unit_fn(observation) == "m³/s"

    # None-safe when deciles are missing entirely or lack thresholds.
    assert description.value_fn(_observation()) is None
    assert description.value_fn(_observation(deciles=HydroDeciles())) is None
    assert description.unit_fn(_observation()) is None


@pytest.mark.parametrize(
    ("key", "expected_enabled_default"),
    [
        ("mq", True),
        ("mnq", True),
        ("nm7q", False),
        ("nm30q", False),
        ("mw", True),
        ("mnw", True),
        ("nq", False),
        ("median_q", False),
        ("nw", False),
        ("median_w", False),
        ("min_q_calendar_day", False),
        ("median_q_calendar_day", False),
        ("max_q_calendar_day", False),
        ("median_w_calendar_day", False),
        ("sum_d", False),
        ("sum_v", False),
        ("days_below_glw", False),
        ("depth_below_ground", True),
    ],
)
def test_historical_statistic_descriptions(
    key: str, expected_enabled_default: bool
) -> None:
    """Test the official historical-statistic(-shaped) sensor descriptions.

    Covers both berechneEinzelwertNummer quantities (HydroDerivedValue) and
    the calendar-day envelope (HydroCalendarDayValue): both models expose
    the same value/unit attribute names, so _historical_statistic/
    _historical_statistic_unit work identically for either. MQ/MNQ/MW/MNW
    and depth-below-ground are enabled by default (usually available and
    broadly useful for their measurement type); the rest stay disabled to
    keep the default device page focused on everyday values -- see
    tests/test_entity.py for the per-measurement-type override that keeps
    the enabled-by-default ones off on a type they don't even apply to.
    """
    description = _description(key)
    is_calendar_day = key.endswith("_calendar_day")
    model = HydroCalendarDayValue if is_calendar_day else HydroDerivedValue

    assert description.translation_key == key
    assert description.entity_registry_enabled_default == expected_enabled_default
    assert description.entity_category is None
    assert description.state_class == SensorStateClass.MEASUREMENT

    stat = model(value=46.41388, unit="m³/s", error=None)
    observation = _observation(**{key: stat})
    assert description.value_fn(observation) == pytest.approx(46.41388)
    assert description.unit_fn(observation) == "m³/s"

    # None-safe when the quantity is absent (e.g. unsupported measurement type).
    assert description.value_fn(_observation()) is None
    assert description.unit_fn(_observation()) is None


def test_below_glw_description() -> None:
    """Test the 'unter GlW' waterway-navigation sensor description.

    Plain string sensor, same reasoning as official_development_7d:
    NIWIS's vocabulary beyond the one observed sample ("unterhalb") is
    unconfirmed, so no device_class/options are declared yet.
    """
    description = _description("below_glw")

    assert description.translation_key == "below_glw"
    assert description.device_class is None
    assert description.options is None
    assert description.entity_registry_enabled_default is False

    observation = _observation(below_glw="unterhalb")
    assert description.value_fn(observation) == "unterhalb"
    assert description.unit_fn(observation) is None
    assert description.value_fn(_observation()) is None


@pytest.mark.parametrize("key", ["nm7q", "nm30q"])
def test_dated_extreme_descriptions_still_report_plain_value(key: str) -> None:
    """Test that nm7q/nm30q's value_fn/unit_fn are unaffected by the new *_dated fields.

    The occurred_from/occurred_to context lives entirely in
    extra_state_attributes (see tests/test_entity.py); the description's
    value_fn/unit_fn keep reading the plain HydroDerivedValue as before.
    """
    description = _description(key)
    stat = HydroDerivedValue(value=15.26, unit="m³/s", error=None)

    assert description.value_fn(_observation(**{key: stat})) == pytest.approx(15.26)
    assert description.unit_fn(_observation(**{key: stat})) == "m³/s"


@pytest.mark.parametrize(
    ("key", "stat_key"),
    [
        ("percent_of_mq", "mq"),
        ("percent_of_mnq", "mnq"),
        ("percent_of_mw", "mw"),
        ("percent_of_mnw", "mnw"),
    ],
)
def test_percent_of_statistic_descriptions(key: str, stat_key: str) -> None:
    """Test the current-value-as-%-of-historical-statistic sensor descriptions."""
    description = _description(key)

    assert description.translation_key == key
    assert description.entity_registry_enabled_default is True
    assert description.entity_category is None
    assert description.state_class == SensorStateClass.MEASUREMENT

    stat = HydroDerivedValue(value=100.0, unit="m³/s", error=None)
    observation = _observation(value=72.3, **{stat_key: stat})
    assert description.value_fn(observation) == pytest.approx(72.3)
    assert description.unit_fn(observation) == PERCENTAGE

    # None-safe when the statistic is absent, the current value is absent, or
    # the statistic is exactly zero (division-by-zero guard).
    assert description.value_fn(_observation()) is None
    assert description.value_fn(_observation(value=None, **{stat_key: stat})) is None
    zero_stat = HydroDerivedValue(value=0.0, unit="m³/s", error=None)
    assert description.value_fn(_observation(value=72.3, **{stat_key: zero_stat})) is None


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

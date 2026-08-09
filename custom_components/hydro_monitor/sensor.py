"""Sensor platform for Hydro Monitor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import HydroMonitorConfigEntry
from .const import DOMAIN, MEASUREMENT_STALE_AFTER
from .coordinator import HydroMonitorCoordinator
from .localization import (
    device_display_name,
    device_model,
    measurement_type_name,
    resolve_language,
)
from .models import HydroMeasurementType, HydroObservation
from .providers.niwis.const import (
    CALENDAR_DAY_STATISTIC_MEASUREMENT_TYPES,
    DECILES_MEASUREMENT_TYPES,
    DEPTH_BELOW_GROUND_MEASUREMENT_TYPES,
    HISTORICAL_STATISTIC_MEASUREMENT_TYPES,
    HISTORICAL_STATISTIC_NIWIS_NAMES,
    LOW_WATER_CLASS_KEYS,
    OFFICIAL_DEVELOPMENT_7D_MEASUREMENT_TYPES,
    SUM_MEASUREMENT_TYPES,
    WATERWAY_INDICATOR_MEASUREMENT_TYPES,
)
from .sensor_glossary import sensor_description

PARALLEL_UPDATES = 0

PRIMARY_TRANSLATION_KEYS: Final = {
    HydroMeasurementType.DISCHARGE: "discharge",
    HydroMeasurementType.WATER_LEVEL: "water_level",
    HydroMeasurementType.GROUNDWATER_LEVEL: "groundwater_level",
    HydroMeasurementType.SPRING_DISCHARGE: "spring_discharge",
}

TREND_SENSOR_KEYS: Final = frozenset({"change_1d", "change_7d"})


def _trend_mm(change_m: float | None) -> int | None:
    """Convert a trend value from metres to millimetres."""
    if change_m is None:
        return None

    return round(change_m * 1000)


def _trend_icon(change_mm: float | int | None) -> str:
    """Return a direction and strength icon for a trend in millimetres."""
    if change_mm is None:
        return "mdi:trending-neutral"

    absolute_change = abs(float(change_mm))

    if absolute_change < 2:
        return "mdi:trending-neutral"

    if change_mm > 0:
        if absolute_change >= 25:
            return "mdi:arrow-up-bold"
        if absolute_change >= 10:
            return "mdi:arrow-up"
        return "mdi:arrow-up-thin"

    if absolute_change >= 25:
        return "mdi:arrow-down-bold"
    if absolute_change >= 10:
        return "mdi:arrow-down"
    return "mdi:arrow-down-thin"


TREND_STATE_OPTIONS: Final = [
    "strong_rising",
    "rising",
    "stable",
    "falling",
    "strong_falling",
]


def _trend_state(
    observation: HydroObservation,
) -> str | None:
    """Return a categorized seven-day trend state."""
    change_mm = _trend_mm(observation.change_7d)

    if change_mm is None:
        return None

    if change_mm >= 25:
        return "strong_rising"

    if change_mm >= 2:
        return "rising"

    if change_mm <= -25:
        return "strong_falling"

    if change_mm <= -2:
        return "falling"

    return "stable"


def _measurement_datetime(
    observation: HydroObservation,
) -> datetime | None:
    """Return the observation date as an aware datetime."""
    observed_on = observation.observed_on

    if observed_on is None:
        return None

    if isinstance(observed_on, datetime):
        if observed_on.tzinfo is None:
            return observed_on.replace(tzinfo=UTC)

        return observed_on.astimezone(UTC)

    return datetime.combine(
        observed_on,
        time.min,
        tzinfo=UTC,
    )


def _measurement_age_hours(
    observation: HydroObservation,
) -> float | None:
    """Return the age of the latest observation in hours."""
    observed_at = _measurement_datetime(observation)

    if observed_at is None:
        return None

    age = dt_util.utcnow() - observed_at

    return round(
        max(age.total_seconds(), 0) / 3600,
        1,
    )


def _static_boundary(index: int) -> Callable[[HydroObservation], float | None]:
    """Return a value_fn reading one static low-water threshold."""

    def _value(observation: HydroObservation) -> float | None:
        boundaries = observation.boundaries
        if boundaries is None or boundaries.static_thresholds is None:
            return None
        return boundaries.static_thresholds[index]

    return _value


def _dynamic_boundary(index: int) -> Callable[[HydroObservation], float | None]:
    """Return a value_fn reading one dynamic low-water threshold."""

    def _value(observation: HydroObservation) -> float | None:
        boundaries = observation.boundaries
        if boundaries is None or boundaries.dynamic_thresholds is None:
            return None
        return boundaries.dynamic_thresholds[index]

    return _value


def _static_boundary_unit(observation: HydroObservation) -> str | None:
    """Return the unit of the static low-water thresholds."""
    return observation.boundaries.static_unit if observation.boundaries else None


def _dynamic_boundary_unit(observation: HydroObservation) -> str | None:
    """Return the unit of the dynamic low-water thresholds."""
    return observation.boundaries.dynamic_unit if observation.boundaries else None


def _historical_statistic(key: str) -> Callable[[HydroObservation], float | None]:
    """Return a value_fn reading one historical-statistic quantity."""

    def _value(observation: HydroObservation) -> float | None:
        stat = getattr(observation, key)
        return stat.value if stat is not None else None

    return _value


def _historical_statistic_unit(key: str) -> Callable[[HydroObservation], str | None]:
    """Return a unit_fn reading one historical-statistic quantity's unit."""

    def _unit(observation: HydroObservation) -> str | None:
        stat = getattr(observation, key)
        return stat.unit if stat is not None else None

    return _unit


HISTORICAL_STATISTIC_KEYS: Final = frozenset(HISTORICAL_STATISTIC_NIWIS_NAMES) | frozenset(
    {
        "min_q_calendar_day",
        "median_q_calendar_day",
        "max_q_calendar_day",
        "median_w_calendar_day",
        "sum_d",
        "sum_v",
        "days_below_glw",
        "depth_below_ground",
    }
)


def _percent_of_statistic(key: str) -> Callable[[HydroObservation], float | None]:
    """Return a value_fn expressing the current value as % of one historical statistic.

    Purely local arithmetic on already-fetched HydroDerivedValue fields
    (mq/mnq/mw/mnw) -- no new API call. None-safe when the statistic is
    missing/errored, the current value is missing, or the statistic is
    exactly zero (guards a division by zero rather than assuming NIWIS
    never returns it).
    """

    def _value(observation: HydroObservation) -> float | None:
        stat = getattr(observation, key)
        if stat is None or not stat.value:
            return None
        if observation.value is None:
            return None
        return observation.value / stat.value * 100

    return _value


def _decile(index: int) -> Callable[[HydroObservation], float | None]:
    """Return a value_fn reading one decile threshold point."""

    def _value(observation: HydroObservation) -> float | None:
        deciles = observation.deciles
        if deciles is None or deciles.thresholds is None:
            return None
        return deciles.thresholds[index]

    return _value


def _decile_unit(observation: HydroObservation) -> str | None:
    """Return the unit of the decile thresholds."""
    return observation.deciles.unit if observation.deciles else None


DECILE_PERCENTILES: Final = (0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)


# Which measurement types a given sensor key is ever fetched/possible for --
# reuses the same gating dicts providers/niwis/const.py already uses to
# decide whether to fetch a quantity at all (and therefore whether it can
# ever have a value). A key absent here applies to all four measurement
# types (value, trends, 30-day min/max, low_water_class, classification
# boundaries, last_measurement, measurement_age). Used below to make sure a
# quantity is never enabled by default on a device it can never apply to,
# regardless of the entity description's own static default.
_KEY_MEASUREMENT_TYPES: Final[dict[str, frozenset[str]]] = {
    **HISTORICAL_STATISTIC_MEASUREMENT_TYPES,
    **CALENDAR_DAY_STATISTIC_MEASUREMENT_TYPES,
    "official_development_7d": OFFICIAL_DEVELOPMENT_7D_MEASUREMENT_TYPES,
    "sum_d": SUM_MEASUREMENT_TYPES,
    "sum_v": SUM_MEASUREMENT_TYPES,
    "below_glw": WATERWAY_INDICATOR_MEASUREMENT_TYPES,
    "days_below_glw": WATERWAY_INDICATOR_MEASUREMENT_TYPES,
    "depth_below_ground": DEPTH_BELOW_GROUND_MEASUREMENT_TYPES,
    **{
        f"percent_of_{stat}": types
        for stat, types in HISTORICAL_STATISTIC_MEASUREMENT_TYPES.items()
    },
    **{f"decile_p{p}": DECILES_MEASUREMENT_TYPES for p in DECILE_PERCENTILES},
}


def _key_applies_to_measurement_type(
    key: str, measurement_type: HydroMeasurementType
) -> bool:
    """Return whether a sensor key is ever fetched/possible for this type."""
    applicable = _KEY_MEASUREMENT_TYPES.get(key)
    return applicable is None or measurement_type.value in applicable


@dataclass(frozen=True, kw_only=True)
class HydroSensorEntityDescription(SensorEntityDescription):
    """Describe a Hydro Monitor sensor entity."""

    value_fn: Callable[[HydroObservation], Any]
    unit_fn: Callable[[HydroObservation], str | None]
    options: list[str] | None = None
    is_primary: bool = False


@dataclass(frozen=True, kw_only=True)
class HydroStationSensorEntityDescription(SensorEntityDescription):
    """Describe a Hydro Monitor station sensor."""

    value_fn: Callable[[HydroMonitorCoordinator], Any]


_DECILE_SENSOR_DESCRIPTIONS: Final = tuple(
    HydroSensorEntityDescription(
        key=f"decile_p{percentile}",
        translation_key=f"decile_p{percentile}",
        name=None,
        icon="mdi:chart-bell-curve-cumulative",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_decile(index),
        unit_fn=_decile_unit,
    )
    for index, percentile in enumerate(DECILE_PERCENTILES)
)


SENSOR_DESCRIPTIONS = (
    HydroSensorEntityDescription(
        key="value",
        name=None,
        icon="mdi:waves-arrow-up",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.value,
        unit_fn=lambda observation: observation.unit,
        is_primary=True,
    ),
    HydroSensorEntityDescription(
        key="change_1d",
        translation_key="trend_1_day",
        name=None,
        icon="mdi:trending-neutral",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: _trend_mm(observation.change_1d),
        unit_fn=lambda observation: "mm",
    ),
    HydroSensorEntityDescription(
        key="change_7d",
        translation_key="trend_7_days",
        name=None,
        icon="mdi:trending-neutral",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: _trend_mm(observation.change_7d),
        unit_fn=lambda observation: "mm",
    ),
    HydroSensorEntityDescription(
        key="trend_state",
        translation_key="water_level_trend",
        name=None,
        icon="mdi:chart-timeline-variant",
        device_class=SensorDeviceClass.ENUM,
        options=TREND_STATE_OPTIONS,
        value_fn=_trend_state,
        unit_fn=lambda observation: None,
    ),
    HydroSensorEntityDescription(
        key="maximum_30d",
        translation_key="high_30_days",
        name=None,
        icon="mdi:arrow-collapse-up",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.maximum_30d,
        unit_fn=lambda observation: observation.unit,
    ),
    HydroSensorEntityDescription(
        key="minimum_30d",
        translation_key="low_30_days",
        name=None,
        icon="mdi:arrow-collapse-down",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.minimum_30d,
        unit_fn=lambda observation: observation.unit,
    ),
    HydroSensorEntityDescription(
        key="low_water_class",
        translation_key="low_water_class",
        name=None,
        icon="mdi:water-alert-outline",
        device_class=SensorDeviceClass.ENUM,
        options=list(LOW_WATER_CLASS_KEYS),
        value_fn=lambda observation: observation.low_water_class,
        unit_fn=lambda observation: None,
    ),
    HydroSensorEntityDescription(
        key="official_development_7d",
        translation_key="official_development_7d",
        name=None,
        icon="mdi:water-check-outline",
        value_fn=lambda observation: observation.official_development_7d,
        unit_fn=lambda observation: None,
    ),
    HydroSensorEntityDescription(
        key="boundary_static_extremely_low",
        translation_key="boundary_static_extremely_low",
        name=None,
        icon="mdi:ruler",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_static_boundary(0),
        unit_fn=_static_boundary_unit,
    ),
    HydroSensorEntityDescription(
        key="boundary_static_very_low",
        translation_key="boundary_static_very_low",
        name=None,
        icon="mdi:ruler",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_static_boundary(1),
        unit_fn=_static_boundary_unit,
    ),
    HydroSensorEntityDescription(
        key="boundary_static_low",
        translation_key="boundary_static_low",
        name=None,
        icon="mdi:ruler",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_static_boundary(2),
        unit_fn=_static_boundary_unit,
    ),
    HydroSensorEntityDescription(
        key="boundary_dynamic_extremely_low",
        translation_key="boundary_dynamic_extremely_low",
        name=None,
        icon="mdi:chart-line-variant",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_dynamic_boundary(0),
        unit_fn=_dynamic_boundary_unit,
    ),
    HydroSensorEntityDescription(
        key="boundary_dynamic_very_low",
        translation_key="boundary_dynamic_very_low",
        name=None,
        icon="mdi:chart-line-variant",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_dynamic_boundary(1),
        unit_fn=_dynamic_boundary_unit,
    ),
    HydroSensorEntityDescription(
        key="boundary_dynamic_low",
        translation_key="boundary_dynamic_low",
        name=None,
        icon="mdi:chart-line-variant",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_dynamic_boundary(2),
        unit_fn=_dynamic_boundary_unit,
    ),
    *_DECILE_SENSOR_DESCRIPTIONS,
    HydroSensorEntityDescription(
        key="mq",
        translation_key="mq",
        name=None,
        icon="mdi:chart-timeline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_historical_statistic("mq"),
        unit_fn=_historical_statistic_unit("mq"),
    ),
    HydroSensorEntityDescription(
        key="mnq",
        translation_key="mnq",
        name=None,
        icon="mdi:water-minus-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_historical_statistic("mnq"),
        unit_fn=_historical_statistic_unit("mnq"),
    ),
    HydroSensorEntityDescription(
        key="nm7q",
        translation_key="nm7q",
        name=None,
        icon="mdi:calendar-week",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("nm7q"),
        unit_fn=_historical_statistic_unit("nm7q"),
    ),
    HydroSensorEntityDescription(
        key="nm30q",
        translation_key="nm30q",
        name=None,
        icon="mdi:calendar-range",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("nm30q"),
        unit_fn=_historical_statistic_unit("nm30q"),
    ),
    HydroSensorEntityDescription(
        key="mw",
        translation_key="mw",
        name=None,
        icon="mdi:chart-timeline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_historical_statistic("mw"),
        unit_fn=_historical_statistic_unit("mw"),
    ),
    HydroSensorEntityDescription(
        key="mnw",
        translation_key="mnw",
        name=None,
        icon="mdi:water-minus-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_historical_statistic("mnw"),
        unit_fn=_historical_statistic_unit("mnw"),
    ),
    HydroSensorEntityDescription(
        key="percent_of_mq",
        translation_key="percent_of_mq",
        name=None,
        icon="mdi:percent-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_percent_of_statistic("mq"),
        unit_fn=lambda observation: PERCENTAGE,
    ),
    HydroSensorEntityDescription(
        key="percent_of_mnq",
        translation_key="percent_of_mnq",
        name=None,
        icon="mdi:percent-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_percent_of_statistic("mnq"),
        unit_fn=lambda observation: PERCENTAGE,
    ),
    HydroSensorEntityDescription(
        key="percent_of_mw",
        translation_key="percent_of_mw",
        name=None,
        icon="mdi:percent-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_percent_of_statistic("mw"),
        unit_fn=lambda observation: PERCENTAGE,
    ),
    HydroSensorEntityDescription(
        key="percent_of_mnw",
        translation_key="percent_of_mnw",
        name=None,
        icon="mdi:percent-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_percent_of_statistic("mnw"),
        unit_fn=lambda observation: PERCENTAGE,
    ),
    HydroSensorEntityDescription(
        key="nq",
        translation_key="nq",
        name=None,
        icon="mdi:arrow-down-bold-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("nq"),
        unit_fn=_historical_statistic_unit("nq"),
    ),
    HydroSensorEntityDescription(
        key="median_q",
        translation_key="median_q",
        name=None,
        icon="mdi:chart-bell-curve",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("median_q"),
        unit_fn=_historical_statistic_unit("median_q"),
    ),
    HydroSensorEntityDescription(
        key="nw",
        translation_key="nw",
        name=None,
        icon="mdi:arrow-down-bold-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("nw"),
        unit_fn=_historical_statistic_unit("nw"),
    ),
    HydroSensorEntityDescription(
        key="median_w",
        translation_key="median_w",
        name=None,
        icon="mdi:chart-bell-curve",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("median_w"),
        unit_fn=_historical_statistic_unit("median_w"),
    ),
    HydroSensorEntityDescription(
        key="min_q_calendar_day",
        translation_key="min_q_calendar_day",
        name=None,
        icon="mdi:calendar-arrow-down",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("min_q_calendar_day"),
        unit_fn=_historical_statistic_unit("min_q_calendar_day"),
    ),
    HydroSensorEntityDescription(
        key="median_q_calendar_day",
        translation_key="median_q_calendar_day",
        name=None,
        icon="mdi:calendar-blank",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("median_q_calendar_day"),
        unit_fn=_historical_statistic_unit("median_q_calendar_day"),
    ),
    HydroSensorEntityDescription(
        key="max_q_calendar_day",
        translation_key="max_q_calendar_day",
        name=None,
        icon="mdi:calendar-arrow-up",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("max_q_calendar_day"),
        unit_fn=_historical_statistic_unit("max_q_calendar_day"),
    ),
    HydroSensorEntityDescription(
        key="median_w_calendar_day",
        translation_key="median_w_calendar_day",
        name=None,
        icon="mdi:calendar-blank",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("median_w_calendar_day"),
        unit_fn=_historical_statistic_unit("median_w_calendar_day"),
    ),
    HydroSensorEntityDescription(
        key="sum_d",
        translation_key="sum_d",
        name=None,
        icon="mdi:water-alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("sum_d"),
        unit_fn=_historical_statistic_unit("sum_d"),
    ),
    HydroSensorEntityDescription(
        key="sum_v",
        translation_key="sum_v",
        name=None,
        icon="mdi:waves",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("sum_v"),
        unit_fn=_historical_statistic_unit("sum_v"),
    ),
    HydroSensorEntityDescription(
        key="below_glw",
        translation_key="below_glw",
        name=None,
        icon="mdi:ferry",
        entity_registry_enabled_default=False,
        value_fn=lambda observation: observation.below_glw,
        unit_fn=lambda observation: None,
    ),
    HydroSensorEntityDescription(
        key="days_below_glw",
        translation_key="days_below_glw",
        name=None,
        icon="mdi:calendar-alert",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        value_fn=_historical_statistic("days_below_glw"),
        unit_fn=_historical_statistic_unit("days_below_glw"),
    ),
    HydroSensorEntityDescription(
        key="depth_below_ground",
        translation_key="depth_below_ground",
        name=None,
        icon="mdi:arrow-collapse-down",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_historical_statistic("depth_below_ground"),
        unit_fn=_historical_statistic_unit("depth_below_ground"),
    ),
    HydroSensorEntityDescription(
        key="last_measurement",
        translation_key="last_measurement",
        name=None,
        icon="mdi:clock-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_measurement_datetime,
        unit_fn=lambda observation: None,
    ),
    HydroSensorEntityDescription(
        key="measurement_age",
        translation_key="measurement_age",
        name=None,
        icon="mdi:clock-alert-outline",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_measurement_age_hours,
        unit_fn=lambda observation: UnitOfTime.HOURS,
    ),
)


def _format_license(value: str | None) -> str | None:
    """Return a human-readable license name."""
    if value is None:
        return None

    normalized = value.strip().lower()

    known_licenses = {
        "cc-by/4.0": "CC BY 4.0",
        "dl-de/by-2-0": "DL-DE/BY-2.0",
    }

    return known_licenses.get(normalized, value)


def _historical_low_discharge(
    coordinator: HydroMonitorCoordinator,
) -> float | None:
    """Return the historical low discharge for applicable stations."""
    if coordinator.measurement_type not in {
        HydroMeasurementType.DISCHARGE,
        HydroMeasurementType.SPRING_DISCHARGE,
    }:
        return None

    return coordinator.station.historical_low_discharge


def _historical_low_discharge_date(
    coordinator: HydroMonitorCoordinator,
) -> Any:
    """Return the date of the historical low discharge."""
    if coordinator.measurement_type not in {
        HydroMeasurementType.DISCHARGE,
        HydroMeasurementType.SPRING_DISCHARGE,
    }:
        return None

    return coordinator.station.historical_low_discharge_date


def _historical_low_water_level(
    coordinator: HydroMonitorCoordinator,
) -> float | None:
    """Return the historical low water level for applicable stations."""
    if coordinator.measurement_type is not HydroMeasurementType.WATER_LEVEL:
        return None

    return coordinator.station.historical_low_water_level


def _historical_low_water_level_date(
    coordinator: HydroMonitorCoordinator,
) -> Any:
    """Return the date of the historical low water level."""
    if coordinator.measurement_type is not HydroMeasurementType.WATER_LEVEL:
        return None

    return coordinator.station.historical_low_water_level_date


def _waterbody_position(
    coordinator: HydroMonitorCoordinator,
) -> float | None:
    """Return the station position on the waterbody in kilometres."""
    value = coordinator.station.waterbody_position

    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


STATION_SENSOR_DESCRIPTIONS = (
    HydroStationSensorEntityDescription(
        key="station_type",
        translation_key="station_type",
        icon="mdi:map-marker-radius",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.station.station_type,
    ),
    HydroStationSensorEntityDescription(
        key="locality",
        translation_key="locality",
        icon="mdi:home-map-marker",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.station.locality,
    ),
    HydroStationSensorEntityDescription(
        key="operator",
        translation_key="operator",
        icon="mdi:office-building",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.station.operator,
    ),
    HydroStationSensorEntityDescription(
        key="institution",
        translation_key="institution",
        icon="mdi:domain",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.station.institution,
    ),
    HydroStationSensorEntityDescription(
        key="license_name",
        translation_key="license",
        icon="mdi:license",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: _format_license(coordinator.station.license_name),
    ),
    HydroStationSensorEntityDescription(
        key="waterbody",
        translation_key="waterbody",
        icon="mdi:waves",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.station.waterbody,
    ),
    HydroStationSensorEntityDescription(
        key="waterbody_code",
        translation_key="waterbody_code",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.station.waterbody_code,
    ),
    HydroStationSensorEntityDescription(
        key="waterbody_position",
        translation_key="waterbody_position",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement="km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=_waterbody_position,
    ),
    HydroStationSensorEntityDescription(
        key="catchment_area",
        translation_key="catchment_area",
        icon="mdi:image-filter-hdr",
        native_unit_of_measurement="km²",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda coordinator: coordinator.station.catchment_area_km2,
    ),
    HydroStationSensorEntityDescription(
        key="gauge_zero_elevation",
        translation_key="gauge_zero_elevation",
        icon="mdi:altimeter",
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda coordinator: coordinator.station.gauge_zero_elevation,
    ),
    HydroStationSensorEntityDescription(
        key="elevation_ground",
        translation_key="ground_elevation",
        icon="mdi:terrain",
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda coordinator: coordinator.station.elevation_ground,
    ),
    HydroStationSensorEntityDescription(
        key="elevation_system",
        translation_key="elevation_system",
        icon="mdi:elevation-rise",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.station.elevation_system,
    ),
    HydroStationSensorEntityDescription(
        key="hydrogeological_region",
        translation_key="hydrogeological_region",
        icon="mdi:layers-triple",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.station.hydrogeological_region,
    ),
    HydroStationSensorEntityDescription(
        key="hydrogeological_region_code",
        translation_key="hydrogeological_region_code",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda coordinator: coordinator.station.hydrogeological_region_code,
    ),
    HydroStationSensorEntityDescription(
        key="historical_low_discharge",
        translation_key="historical_low_discharge",
        icon="mdi:waves-arrow-down",
        native_unit_of_measurement="m³/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_historical_low_discharge,
    ),
    HydroStationSensorEntityDescription(
        key="historical_low_discharge_date",
        translation_key="historical_low_discharge_date",
        icon="mdi:calendar-arrow-down",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_historical_low_discharge_date,
    ),
    HydroStationSensorEntityDescription(
        key="historical_low_water_level",
        translation_key="historical_low_water_level",
        icon="mdi:arrow-collapse-down",
        native_unit_of_measurement="m",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_historical_low_water_level,
    ),
    HydroStationSensorEntityDescription(
        key="historical_low_water_level_date",
        translation_key="historical_low_water_level_date",
        icon="mdi:calendar-arrow-down",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_historical_low_water_level_date,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HydroMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Hydro Monitor sensor entities from a config entry."""
    coordinator = entry.runtime_data.coordinator

    entities = [
        *(
            HydroObservationSensor(coordinator, description)
            for description in SENSOR_DESCRIPTIONS
        ),
        *(
            HydroStationSensor(coordinator, description)
            for description in STATION_SENSOR_DESCRIPTIONS
            if description.value_fn(coordinator) is not None
        ),
    ]

    async_add_entities(entities)


class HydroBaseSensor(
    CoordinatorEntity[HydroMonitorCoordinator],
    SensorEntity,
):
    """Base class for Hydro Monitor sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HydroMonitorCoordinator,
    ) -> None:
        super().__init__(coordinator)

        station = coordinator.station
        measurement_type = coordinator.measurement_type
        language = resolve_language(getattr(coordinator, "hass", None))

        self._station = station
        self._measurement_type = measurement_type
        self._measurement_name = measurement_type_name(measurement_type, language)

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{station.provider}:{station.station_id}:{measurement_type.value}",
                )
            },
            name=device_display_name(station.name, measurement_type, language),
            manufacturer=station.institution or station.provider.upper(),
            model=device_model(measurement_type, language),
            configuration_url=station.source_url,
        )

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available


class HydroObservationSensor(HydroBaseSensor):
    """Represent a Hydro Monitor observation sensor."""

    entity_description: HydroSensorEntityDescription

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HydroMonitorCoordinator,
        description: HydroSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        self._attr_unique_id = (
            f"{coordinator.station.provider}_"
            f"{coordinator.station.station_id}_"
            f"{coordinator.measurement_type.value}_"
            f"{description.key}"
        )

        if description.translation_key is not None:
            self._attr_translation_key = description.translation_key

        if description.options is not None:
            self._attr_options = description.options

    @property
    def icon(self) -> str | None:
        """Return a dynamic icon for trend sensors."""
        if self.entity_description.key in TREND_SENSOR_KEYS:
            return _trend_icon(self.native_value)

        return self.entity_description.icon

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return whether this entity should be enabled by default.

        Never enabled for a measurement type the quantity doesn't apply to
        at all -- it would otherwise clutter the entity list with a
        permanently-unavailable entity (e.g. "% of MQ" on a groundwater
        device, which never fetches MQ in the first place). Otherwise
        defers to the entity description's own default.
        """
        if not _key_applies_to_measurement_type(
            self.entity_description.key, self._measurement_type
        ):
            return False

        return self.entity_description.entity_registry_enabled_default

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self.entity_description.unit_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, Any] | None:
        """Return additional sensor attributes."""
        observation = self.coordinator.data
        key = self.entity_description.key

        if key == "measurement_age":
            age_hours = _measurement_age_hours(observation)
            stale_after_hours = MEASUREMENT_STALE_AFTER.total_seconds() / 3600

            return {
                "stale": (age_hours is not None and age_hours >= stale_after_hours),
                "stale_after_hours": stale_after_hours,
            }

        # Every "official NIWIS derived quantity" sensor below gets a
        # localized `description` attribute, since their names mirror
        # NIWIS's own hydrological abbreviations (MQ, GlW, ...) and Home
        # Assistant has no per-entity tooltip mechanism to explain them
        # beyond this "more info" attribute. See sensor_glossary.py.
        attrs: dict[str, Any] | None = None

        if key == "low_water_class":
            attrs = {
                "raw_value": observation.low_water_class_raw,
                "error": observation.low_water_class_error,
            }
        elif key == "official_development_7d":
            attrs = {
                "raw_value": observation.official_development_7d_raw,
                "error": observation.official_development_7d_error,
            }
        elif key == "below_glw":
            attrs = {
                "raw_value": observation.below_glw_raw,
                "error": observation.below_glw_error,
            }
        elif key.startswith("boundary_static_"):
            boundaries = observation.boundaries
            attrs = {
                "error": boundaries.static_error if boundaries else None,
            }
        elif key.startswith("boundary_dynamic_"):
            boundaries = observation.boundaries
            attrs = {
                "error": boundaries.dynamic_error if boundaries else None,
                "reference_date": (
                    boundaries.dynamic_reference_date.isoformat()
                    if boundaries and boundaries.dynamic_reference_date
                    else None
                ),
            }
        elif key in ("nm7q", "nm30q"):
            stat = getattr(observation, key)
            dated = getattr(observation, f"{key}_dated")
            attrs = {
                "error": stat.error if stat is not None else None,
                "occurred_from": (
                    dated.occurred_from.isoformat()
                    if dated and dated.occurred_from
                    else None
                ),
                "occurred_to": (
                    dated.occurred_to.isoformat()
                    if dated and dated.occurred_to
                    else None
                ),
            }
        elif key in HISTORICAL_STATISTIC_KEYS:
            stat = getattr(observation, key)
            attrs = {"error": stat.error if stat is not None else None}
        elif key.startswith("percent_of_"):
            stat = getattr(observation, key.removeprefix("percent_of_"))
            attrs = {"error": stat.error if stat is not None else None}
        elif key.startswith("decile_p"):
            deciles = observation.deciles
            attrs = {
                "error": deciles.error if deciles else None,
                "reference_date": (
                    deciles.reference_date.isoformat()
                    if deciles and deciles.reference_date
                    else None
                ),
            }

        if attrs is not None:
            description = sensor_description(
                key, resolve_language(getattr(self.coordinator, "hass", None))
            )
            if description is not None:
                attrs["description"] = description
            return attrs

        if not self.entity_description.is_primary:
            return None

        station = self.coordinator.station

        return {
            "provider": station.provider,
            "station_id": station.station_id,
            "observed_on": (
                observation.observed_on.isoformat() if observation.observed_on else None
            ),
            "quality_flag": observation.quality_flag,
            "sample_count": observation.sample_count,
            # Lets this entity be plotted on Home Assistant's map card,
            # which displays any entity carrying latitude/longitude
            # attributes (not just device_tracker/person).
            "latitude": station.latitude,
            "longitude": station.longitude,
        }


class HydroStationSensor(HydroBaseSensor):
    """Represent a Hydro Monitor station metadata sensor."""

    entity_description: HydroStationSensorEntityDescription

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HydroMonitorCoordinator,
        description: HydroStationSensorEntityDescription,
    ) -> None:
        """Initialize the station sensor."""
        super().__init__(coordinator)

        self.entity_description = description

        self._attr_unique_id = (
            f"{coordinator.station.provider}_"
            f"{coordinator.station.station_id}_"
            f"{coordinator.measurement_type.value}_"
            f"station_{description.key}"
        )

        if description.translation_key is not None:
            self._attr_translation_key = description.translation_key

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        return super().available and self.native_value is not None

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
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import HydroMonitorConfigEntry
from .const import DOMAIN, MEASUREMENT_STALE_AFTER
from .coordinator import HydroMonitorCoordinator
from .models import HydroMeasurementType, HydroObservation

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
        value_fn=lambda observation: observation.low_water_class,
        unit_fn=lambda observation: None,
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

        measurement_name = {
            HydroMeasurementType.DISCHARGE: "Discharge",
            HydroMeasurementType.WATER_LEVEL: "Water level",
            HydroMeasurementType.GROUNDWATER_LEVEL: "Groundwater level",
            HydroMeasurementType.SPRING_DISCHARGE: "Spring discharge",
        }[measurement_type]

        self._station = station
        self._measurement_type = measurement_type
        self._measurement_name = measurement_name

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{station.provider}:{station.station_id}:{measurement_type.value}",
                )
            },
            name=station.name,
            manufacturer=station.institution or station.provider.upper(),
            model="Hydrological monitoring station",
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

        if self.entity_description.key == "measurement_age":
            age_hours = _measurement_age_hours(observation)
            stale_after_hours = MEASUREMENT_STALE_AFTER.total_seconds() / 3600

            return {
                "stale": (age_hours is not None and age_hours >= stale_after_hours),
                "stale_after_hours": stale_after_hours,
            }

        if self.entity_description.key == "low_water_class":
            return {"error": observation.low_water_class_error}

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

"""Sensor platform for Hydro Monitor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any, Callable

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

NAMES = {
    HydroMeasurementType.DISCHARGE: "Abfluss",
    HydroMeasurementType.WATER_LEVEL: "Wasserstand",
    HydroMeasurementType.GROUNDWATER_LEVEL: "Grundwasserstand",
    HydroMeasurementType.SPRING_DISCHARGE: "Quellschüttung",
}

TREND_SENSOR_KEYS = {"change_1d", "change_7d"}


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
    is_primary: bool = False


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
        name="Trend 1 Tag",
        icon="mdi:trending-neutral",
        value_fn=lambda observation: (
            round(observation.change_1d * 1000)
            if observation.change_1d is not None
            else None
        ),
        unit_fn=lambda observation: "mm",
    ),
    HydroSensorEntityDescription(
        key="change_7d",
        name="Trend 7 Tage",
        icon="mdi:trending-neutral",
        value_fn=lambda observation: (
            round(observation.change_7d * 1000)
            if observation.change_7d is not None
            else None
        ),
        unit_fn=lambda observation: "mm",
    ),
    HydroSensorEntityDescription(
        key="maximum_30d",
        name="30-Tage-Hoch",
        icon="mdi:arrow-collapse-up",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.maximum_30d,
        unit_fn=lambda observation: observation.unit,
    ),
    HydroSensorEntityDescription(
        key="minimum_30d",
        name="30-Tage-Tief",
        icon="mdi:arrow-collapse-down",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda observation: observation.minimum_30d,
        unit_fn=lambda observation: observation.unit,
    ),
    HydroSensorEntityDescription(
        key="last_measurement",
        name="Letzte Messung",
        icon="mdi:clock-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_measurement_datetime,
        unit_fn=lambda observation: None,
    ),
    HydroSensorEntityDescription(
        key="measurement_age",
        name="Messalter",
        icon="mdi:clock-alert-outline",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_measurement_age_hours,
        unit_fn=lambda observation: UnitOfTime.HOURS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HydroMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Hydro Monitor sensor entities from a config entry."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        HydroObservationSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class HydroObservationSensor(
    CoordinatorEntity[HydroMonitorCoordinator],
    SensorEntity,
):
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

        station = coordinator.station
        measurement_type = coordinator.measurement_type

        if description.is_primary:
            # Keep the existing unique ID of the primary sensor.
            self._attr_unique_id = (
                f"{station.provider}:{station.station_id}:{measurement_type.value}"
            )
            self._attr_name = NAMES[measurement_type]
        else:
            self._attr_unique_id = (
                f"{station.provider}:"
                f"{station.station_id}:"
                f"{measurement_type.value}:"
                f"{description.key}"
            )

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{station.provider}:{station.station_id}",
                )
            },
            name=station.name,
            manufacturer=station.institution or "NIWIS",
            model="Hydrologische Messstelle",
            configuration_url=station.source_url,
        )

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
            "waterbody": station.waterbody,
            "operator": station.operator,
            "institution": station.institution,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "license": station.license_name,
        }

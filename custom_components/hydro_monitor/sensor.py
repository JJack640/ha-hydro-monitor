"""Sensor platform for Hydro Monitor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HydroMonitorConfigEntry
from .const import DOMAIN
from .coordinator import HydroMonitorCoordinator
from .models import HydroMeasurementType, HydroObservation

PARALLEL_UPDATES = 0

NAMES = {
    HydroMeasurementType.DISCHARGE: "Abfluss",
    HydroMeasurementType.WATER_LEVEL: "Wasserstand",
    HydroMeasurementType.GROUNDWATER_LEVEL: "Grundwasserstand",
    HydroMeasurementType.SPRING_DISCHARGE: "Quellschüttung",
}


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
        value_fn=lambda observation: observation.value,
        unit_fn=lambda observation: observation.unit,
        is_primary=True,
    ),
    HydroSensorEntityDescription(
        key="change_1d",
        name="Trend 1 Tag",
        value_fn=lambda observation: observation.change_1d,
        unit_fn=lambda observation: observation.unit,
    ),
    HydroSensorEntityDescription(
        key="change_7d",
        name="Trend 7 Tage",
        value_fn=lambda observation: observation.change_7d,
        unit_fn=lambda observation: observation.unit,
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
    _attr_state_class = SensorStateClass.MEASUREMENT

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
            # Keep the original unique ID so existing dashboards and
            # automations continue to use the same entity.
            self._attr_unique_id = (
                f"{station.provider}:{station.station_id}:{measurement_type.value}"
            )
            self._attr_name = NAMES[measurement_type]
        else:
            self._attr_unique_id = (
                f"{station.provider}:{station.station_id}:"
                f"{measurement_type.value}:{description.key}"
            )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{station.provider}:{station.station_id}")},
            name=station.name,
            manufacturer=station.institution or "NIWIS",
            model="Hydrologische Messstelle",
            configuration_url=station.source_url,
        )

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
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return attributes for the primary observation sensor."""
        if not self.entity_description.is_primary:
            return None

        station = self.coordinator.station
        observation = self.coordinator.data

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

from __future__ import annotations
from homeassistant.components.sensor import SensorEntity,SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import HydroMonitorConfigEntry
from .const import DOMAIN
from .coordinator import HydroMonitorCoordinator
from .models import HydroMeasurementType
PARALLEL_UPDATES=0
NAMES={HydroMeasurementType.DISCHARGE:"Abfluss",HydroMeasurementType.WATER_LEVEL:"Wasserstand",HydroMeasurementType.GROUNDWATER_LEVEL:"Grundwasserstand",HydroMeasurementType.SPRING_DISCHARGE:"Quellschüttung"}
async def async_setup_entry(hass:HomeAssistant,entry:HydroMonitorConfigEntry,async_add_entities:AddConfigEntryEntitiesCallback)->None:async_add_entities([HydroObservationSensor(entry.runtime_data.coordinator)])
class HydroObservationSensor(CoordinatorEntity[HydroMonitorCoordinator],SensorEntity):
 _attr_has_entity_name=True;_attr_state_class=SensorStateClass.MEASUREMENT
 def __init__(self,coordinator):
  super().__init__(coordinator);s=coordinator.station;mt=coordinator.measurement_type;self._attr_name=NAMES[mt];self._attr_unique_id=f"{s.provider}:{s.station_id}:{mt.value}";self._attr_device_info=DeviceInfo(identifiers={(DOMAIN,f"{s.provider}:{s.station_id}")},name=s.name,manufacturer=s.institution or "NIWIS",model="Hydrologische Messstelle",configuration_url=s.source_url)
 @property
 def native_value(self):return self.coordinator.data.value
 @property
 def native_unit_of_measurement(self):return self.coordinator.data.unit
 @property
 def available(self):return super().available and self.coordinator.data.value is not None
 @property
 def extra_state_attributes(self):
  s=self.coordinator.station;o=self.coordinator.data
  return {"provider":s.provider,"station_id":s.station_id,"observed_on":o.observed_on.isoformat() if o.observed_on else None,"quality_flag":o.quality_flag,"change_1d":o.change_1d,"change_7d":o.change_7d,"sample_count":o.sample_count,"waterbody":s.waterbody,"operator":s.operator,"institution":s.institution,"latitude":s.latitude,"longitude":s.longitude,"license":s.license_name}

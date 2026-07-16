from __future__ import annotations
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .const import CONF_MEASUREMENT_TYPE,CONF_STATION_ID
from .coordinator import HydroMonitorCoordinator,async_get_station
from .models import HydroMeasurementType,HydroStation
from .providers.niwis.api import NiwisError
PLATFORMS=[Platform.SENSOR]
@dataclass(slots=True)
class HydroMonitorRuntimeData:
 station:HydroStation; coordinator:HydroMonitorCoordinator
type HydroMonitorConfigEntry=ConfigEntry[HydroMonitorRuntimeData]
async def async_setup_entry(hass:HomeAssistant,entry:HydroMonitorConfigEntry)->bool:
 try:station=await async_get_station(hass,entry.data[CONF_STATION_ID])
 except NiwisError as err:raise ConfigEntryNotReady(str(err)) from err
 mt=HydroMeasurementType(entry.data[CONF_MEASUREMENT_TYPE]); coordinator=HydroMonitorCoordinator(hass,entry,station,mt); await coordinator.async_config_entry_first_refresh()
 entry.runtime_data=HydroMonitorRuntimeData(station,coordinator); await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS); return True
async def async_unload_entry(hass:HomeAssistant,entry:HydroMonitorConfigEntry)->bool:return await hass.config_entries.async_unload_platforms(entry,PLATFORMS)

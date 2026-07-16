from __future__ import annotations
from datetime import date
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator,UpdateFailed
from .const import DEFAULT_UPDATE_INTERVAL
from .models import HydroMeasurementType,HydroObservation,HydroStation
from .providers.niwis.api import NiwisClient,NiwisError
from .providers.niwis.const import HYDRO_TO_NIWIS_ENDPOINT
from .providers.niwis.mapper import observation_from_niwis,station_from_niwis
_LOGGER=logging.getLogger(__name__)
def change(series,days):
 if not series:return None
 try:new=float(str(series[0].get("messwert")).replace(",","."))
 except (TypeError,ValueError):return None
 target=date.today().toordinal()-days
 for x in series[1:]:
  try:d=date.fromisoformat(str(x.get("datum"))[:10]); old=float(str(x.get("messwert")).replace(",","."))
  except (TypeError,ValueError):continue
  if d.toordinal()<=target:return round(new-old,3)
 return None
class HydroMonitorCoordinator(DataUpdateCoordinator[HydroObservation]):
 def __init__(self,hass:HomeAssistant,entry:ConfigEntry,station:HydroStation,mt:HydroMeasurementType)->None:
  self.station=station; self.measurement_type=mt; self.client=NiwisClient(async_get_clientsession(hass))
  super().__init__(hass,_LOGGER,name=f"hydro_monitor_{station.station_id}_{mt.value}",update_interval=DEFAULT_UPDATE_INTERVAL,config_entry=entry)
 async def _async_update_data(self)->HydroObservation:
  try:series=await self.client.async_get_series(HYDRO_TO_NIWIS_ENDPOINT[self.measurement_type.value],self.station.station_id)
  except NiwisError as err:raise UpdateFailed(str(err)) from err
  o=observation_from_niwis(self.measurement_type,series)
  return HydroObservation(o.measurement_type,o.value,o.unit,o.observed_on,o.quality_flag,change(series,1),change(series,7),o.sample_count)
async def async_get_station(hass:HomeAssistant,station_id:str)->HydroStation:
 client=NiwisClient(async_get_clientsession(hass)); return station_from_niwis(await client.async_get_station(station_id))

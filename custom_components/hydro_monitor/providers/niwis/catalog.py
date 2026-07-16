from __future__ import annotations
import asyncio
from datetime import UTC,datetime,timedelta
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util.location import distance
from ...const import CATALOG_CACHE_HOURS,DOMAIN
from ...models import HydroMeasurementType,HydroStation
from .api import NiwisClient,NiwisError
from .const import HYDRO_TO_NIWIS_TYPE
from .mapper import station_from_niwis
class NiwisCatalog:
 def __init__(self,hass:HomeAssistant)->None:
  self.hass=hass; self.client=NiwisClient(async_get_clientsession(hass)); self.store=Store(hass,1,f"{DOMAIN}.niwis_catalog"); self.details={}
 async def async_nearby_stations(self,mt:HydroMeasurementType,limit:int)->list[HydroStation]:
  cached=await self.store.async_load() or {}; self.details=cached.get("details",{})
  catalog=await self.client.async_get_station_catalog(); native=HYDRO_TO_NIWIS_TYPE[mt.value]
  candidates=[x for x in catalog if native in (x.get("messgroesse") or [])]
  missing=[x for x in candidates if x["messstelleNr"] not in self.details]; sem=asyncio.Semaphore(8)
  async def fetch(x):
   async with sem:
    try:self.details[x["messstelleNr"]]=await self.client.async_get_station(x["messstelleNr"])
    except NiwisError:return
  if missing:
   await asyncio.gather(*(fetch(x) for x in missing)); await self.store.async_save({"loaded_at":datetime.now(UTC).isoformat(),"details":self.details})
  out=[]
  for x in candidates:
   d=self.details.get(x["messstelleNr"])
   if not d:continue
   s=station_from_niwis(d)
   if s.latitude is None or s.longitude is None:continue
   km=distance(self.hass.config.latitude,self.hass.config.longitude,s.latitude,s.longitude)
   out.append(station_from_niwis(d,round(km,1)))
  out.sort(key=lambda s:(s.distance_km if s.distance_km is not None else 1e9,s.name.casefold()))
  return out[:limit]

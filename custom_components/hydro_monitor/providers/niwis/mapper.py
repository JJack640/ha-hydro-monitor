from __future__ import annotations
from datetime import date
from typing import Any
from ...models import HydroMeasurementType,HydroObservation,HydroStation
from .const import NIWIS_TO_HYDRO_TYPE
def as_float(v:Any)->float|None:
 try:return float(str(v).replace(",","."))
 except (TypeError,ValueError):return None
def station_from_niwis(data:dict[str,Any],distance_km:float|None=None)->HydroStation:
 types=tuple(HydroMeasurementType(NIWIS_TO_HYDRO_TYPE[x]) for x in data.get("messgroesse",[]) if x in NIWIS_TO_HYDRO_TYPE)
 return HydroStation("niwis",str(data["messstelleNr"]),str(data.get("name") or data["messstelleNr"]),types,as_float(data.get("breite")),as_float(data.get("laenge")),data.get("gewaesser"),data.get("betreiber"),data.get("institution"),data.get("urlMessstelle"),data.get("lizenz"),distance_km)
def observation_from_niwis(mt:HydroMeasurementType,series:list[dict[str,Any]])->HydroObservation:
 if not series:return HydroObservation(mt,None,None,None)
 n=series[0]
 try:d=date.fromisoformat(str(n.get("datum"))[:10])
 except ValueError:d=None
 return HydroObservation(mt,as_float(n.get("messwert")),n.get("einheit"),d,n.get("flag"),sample_count=len(series))

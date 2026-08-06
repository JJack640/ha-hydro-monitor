BASE_URL="https://niwis-online.de/api/daten"
NIWIS_TO_HYDRO_TYPE={"Abfluss":"discharge","Wasserstand":"water_level","Grundwasserstand":"groundwater_level","Quellschüttung":"spring_discharge"}
HYDRO_TO_NIWIS_TYPE={v:k for k,v in NIWIS_TO_HYDRO_TYPE.items()}
HYDRO_TO_NIWIS_ENDPOINT={"discharge":"abfluss","water_level":"wasserstand","groundwater_level":"grundwasserstand","spring_discharge":"quellschuettung"}

DERIVED_ENDPOINT_LOW_WATER_CLASS="berechneEinzelwertKategorie"
HYDRO_TO_NIWIS_LOW_WATER_CLASS_QUANTITY={"discharge":"Abfluss Niedrigwasserklasse aktueller Tag","water_level":"Wasserstand Niedrigwasserklasse aktueller Tag","groundwater_level":"Grundwasser Niedrigwasserklasse aktueller Tag","spring_discharge":"Quellschüttung Niedrigwasserklasse aktueller Tag"}
# Reference period required by berechneEinzelwertKategorie. Matches
# tools/niwis_discovery.py's probing assumption; NOT confirmed as NIWIS's
# authoritative default (docs/niwis_reference.md §7.16 item 3, §11.6).
# Not user-configurable in Sprint 1.
DERIVED_YEAR_DEFINITION="KALENDERJAHR"
DERIVED_REFERENCE_START_YEAR=1991
DERIVED_REFERENCE_END_YEAR=2020

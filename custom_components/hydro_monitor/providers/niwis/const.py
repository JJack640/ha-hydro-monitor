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

# Shared vocabulary for the official NIWIS low-water classification scheme,
# used both by the current-day classification (berechneEinzelwertKategorie)
# and the classification-boundary endpoints. NIWIS is inconsistent about
# capitalization of "kein Niedrigwasser" across endpoints, so lookups must
# casefold the raw label before indexing this dict.
LOW_WATER_CLASS_LABEL_TO_KEY={"extrem niedrig":"extremely_low","sehr niedrig":"very_low","niedrig":"low","kein niedrigwasser":"no_low_water"}
LOW_WATER_CLASS_KEYS=tuple(LOW_WATER_CLASS_LABEL_TO_KEY.values())

DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC="berechneKlassifikationsgrenzeStatisch"
DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC="berechneKlassifikationsgrenzeDynamisch"
HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_STATIC_QUANTITY={"discharge":"Abfluss Klassifikation mit statischen Grenzwerten","water_level":"Wasserstand Klassifikation mit statischen Grenzwerten","groundwater_level":"Grundwasserstand Klassifikation mit statischen Grenzwerten","spring_discharge":"Quellschüttung Klassifikation mit statischen Grenzwerten"}
# berechneKlassifikationsgrenzeDynamisch is SHARED/OVERLOADED: it also serves
# "... Dezile tageweise" (deciles, 10-class, Sprint 5 — out of scope). Only
# ever request the quantity names below; a future deciles constant must be
# a SEPARATE dict, never merged into this one.
HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_DYNAMIC_QUANTITY={"discharge":"Abfluss Klassifikation mit variablen Grenzwerten","water_level":"Wasserstand Klassifikation mit variablen Grenzwerten","groundwater_level":"Grundwasserstand Klassifikation mit variablen Grenzwerten","spring_discharge":"Quellschüttung Klassifikation mit variablen Grenzwerten"}

# Also serves the unrelated "Entwicklung letzte 7 Tage" quantity (Sprint 3)
# — same endpoint, distinguished only by abgeleiteteGroesse. Only discharge
# and water_level have a catalog entry for this quantity; no reference
# period is required (unlike every other derived quantity above).
HYDRO_TO_NIWIS_OFFICIAL_DEVELOPMENT_7D_QUANTITY={"discharge":"Abfluss Entwicklung letzte 7 Tage","water_level":"Wasserstand Entwicklung letzte 7 Tage"}
OFFICIAL_DEVELOPMENT_7D_MEASUREMENT_TYPES=frozenset({"discharge","water_level"})

DERIVED_ENDPOINT_HISTORICAL_STATISTICS="berechneEinzelwertNummer"
# SHARED/OVERLOADED (same caveat as the boundaries-dynamic endpoint): also
# serves NQ, median_q_statisch, sumd/sumv_zeitfenster, nw, and
# median_w_bezogen_auf_referenzzeitraum — none in scope this sprint.

# MQ/MNQ/NM7Q/NM30Q are discharge-only; MW/MNW are their water_level
# equivalents (mean / mean-low value). No catalog entry exists at all for
# groundwater_level or spring_discharge in this endpoint family. Unlike the
# dicts above, these abgeleiteteGroesse values are fixed literals that do
# not vary by measurement type, so there is nothing to look up per type —
# only applicability to gate.
HISTORICAL_STATISTIC_NIWIS_NAMES={"mq":"MQ","mnq":"MNQ","nm7q":"NM7Q","nm30q":"NM30Q","mw":"MW","mnw":"MNW"}
HISTORICAL_STATISTIC_MEASUREMENT_TYPES={"mq":frozenset({"discharge"}),"mnq":frozenset({"discharge"}),"nm7q":frozenset({"discharge"}),"nm30q":frozenset({"discharge"}),"mw":frozenset({"water_level"}),"mnw":frozenset({"water_level"})}

# NM7Q/NM30Q use benoetigtZeitintervall (von/bis) instead of a reference
# period. LIVE-VERIFIED against the real API (2026-08-07): a bare 7-day
# interval for NM7Q returns hatZuvieleFehlwerte=true (einzelwert "NaN") --
# NIWIS apparently needs a wider analysis window than the statistic's own
# name suggests to compute it (likely searching for the lowest N-day mean
# *within* the requested interval, not treating the interval as the window
# itself). A flat 30-day interval succeeds for BOTH NM7Q and NM30Q
# (confirmed via direct API calls), matching tools/niwis_discovery.py's
# original probing approach -- which this project's own Sprint 4 planning
# had initially (incorrectly) dismissed as a probing-script artifact. Not
# user-configurable in Sprint 4.
HISTORICAL_STATISTIC_INTERVAL_QUANTITIES=frozenset({"nm7q","nm30q"})
HISTORICAL_STATISTIC_INTERVAL_DAYS=30

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
# berechneKlassifikationsgrenzeDynamisch is SHARED/OVERLOADED: it also
# serves "... Dezile tageweise" (deciles, 10-class,
# HYDRO_TO_NIWIS_DECILES_QUANTITY below). Only ever request the quantity
# names in each dict below — never merge the two dicts.
HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_DYNAMIC_QUANTITY={"discharge":"Abfluss Klassifikation mit variablen Grenzwerten","water_level":"Wasserstand Klassifikation mit variablen Grenzwerten","groundwater_level":"Grundwasserstand Klassifikation mit variablen Grenzwerten","spring_discharge":"Quellschüttung Klassifikation mit variablen Grenzwerten"}

# Deciles ("Dezile tageweise") share berechneKlassifikationsgrenzeDynamisch
# with the low-water dynamic boundaries above — kept as a SEPARATE dict per
# that comment's instruction. Only discharge/water_level have a catalog
# entry (same applicability as the boundaries above and Sprint 3's
# official_development_7d).
HYDRO_TO_NIWIS_DECILES_QUANTITY={"discharge":"Abfluss Dezile tageweise","water_level":"Wasserstand Dezile tageweise"}
DECILES_MEASUREMENT_TYPES=frozenset({"discharge","water_level"})
# Expected klassifikationen labels for the deciles shape, in exact NIWIS
# order — guards against the shared/overloaded endpoint ever returning the
# low-water boundaries' 4-class shape here by mistake.
DECILE_CLASS_LABELS=("0-10%","10-20%","20-30%","30-40%","40-50%","50-60%","60-70%","70-80%","80-90%","90-100%")

# Also serves the unrelated "Entwicklung letzte 7 Tage" quantity (Sprint 3)
# — same endpoint, distinguished only by abgeleiteteGroesse. Only discharge
# and water_level have a catalog entry for this quantity; no reference
# period is required (unlike every other derived quantity above).
HYDRO_TO_NIWIS_OFFICIAL_DEVELOPMENT_7D_QUANTITY={"discharge":"Abfluss Entwicklung letzte 7 Tage","water_level":"Wasserstand Entwicklung letzte 7 Tage"}
OFFICIAL_DEVELOPMENT_7D_MEASUREMENT_TYPES=frozenset({"discharge","water_level"})

DERIVED_ENDPOINT_HISTORICAL_STATISTICS="berechneEinzelwertNummer"
# SHARED/OVERLOADED (same caveat as the boundaries-dynamic endpoint): also
# serves SumD/SumV Zeitfenster (below, DERIVED_ENDPOINT_SUM_STATISTICS
# alias for the same string) and the depth-below-ground/waterway-day
# quantities' underlying berechneEinzelwertNummer calls.

# MQ/MNQ/NM7Q/NM30Q/NQ/median_q are discharge-only; MW/MNW/NW/median_w are
# their water_level equivalents (mean / mean-low / absolute-low / median
# value, all over the reference period). No catalog entry exists at all
# for groundwater_level or spring_discharge in this endpoint family.
# median_q/median_w are reference-period-wide single values -- distinct
# from CALENDAR_DAY_STATISTIC_NIWIS_NAMES's day-indexed
# median_q_calendar_day/median_w_calendar_day below despite the similar
# NIWIS name. Unlike the dicts above, these abgeleiteteGroesse values are
# fixed literals that do not vary by measurement type, so there is
# nothing to look up per type — only applicability to gate.
HISTORICAL_STATISTIC_NIWIS_NAMES={"mq":"MQ","mnq":"MNQ","nm7q":"NM7Q","nm30q":"NM30Q","mw":"MW","mnw":"MNW","nq":"NQ","median_q":"Median Q Statisch","nw":"NW","median_w":"Median W bezogen auf Referenzzeitraum"}
HISTORICAL_STATISTIC_MEASUREMENT_TYPES={"mq":frozenset({"discharge"}),"mnq":frozenset({"discharge"}),"nm7q":frozenset({"discharge"}),"nm30q":frozenset({"discharge"}),"mw":frozenset({"water_level"}),"mnw":frozenset({"water_level"}),"nq":frozenset({"discharge"}),"median_q":frozenset({"discharge"}),"nw":frozenset({"water_level"}),"median_w":frozenset({"water_level"})}

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

# Historical calendar-day envelope (Sprint 7 Group A): the historical
# min/median/max value recorded on this exact calendar day across the
# reference period, via a 366-row per-day table (same shape/caching
# rationale as the dynamic low-water boundaries/deciles above, but each
# row is a single plain number rather than a set of thresholds). Min/Max Q
# are discharge-only; NIWIS has no Min/Max W entry in its catalog at all.
DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS="berechneZeitreihenErgebnisNummer"
CALENDAR_DAY_STATISTIC_NIWIS_NAMES={"min_q_calendar_day":"Min Q pro Kalendartag","median_q_calendar_day":"Median Q pro Kalendertag","max_q_calendar_day":"Max Q pro Kalendartag","median_w_calendar_day":"Median W pro Kalendertag"}
CALENDAR_DAY_STATISTIC_MEASUREMENT_TYPES={"min_q_calendar_day":frozenset({"discharge"}),"median_q_calendar_day":frozenset({"discharge"}),"max_q_calendar_day":frozenset({"discharge"}),"median_w_calendar_day":frozenset({"water_level"})}

# NM7Q/NM30Q bundled with the date range they occurred in (Sprint 7 Group
# C). Same berechneEinzelwertKategorie endpoint as low_water_class/
# official_development_7d above, same 30-day interval as plain NM7Q/NM30Q.
# Discharge-only (mirrors HISTORICAL_STATISTIC_MEASUREMENT_TYPES's
# nm7q/nm30q applicability).
HYDRO_TO_NIWIS_DATED_EXTREME_QUANTITY={"nm7q":"NM7Q mit Datum","nm30q":"NM30Q mit Datum"}

# Station-specific cumulative low-water day/volume accumulation over the
# same 30-day window as NM7Q/NM30Q (Sprint 7 Group D). LIVE-VERIFIED
# (2026-08-07, full-year interval): SumD's day-by-day series shows long
# flat plateaus (not a qualifying low-water day) followed by daily
# increments (is one) -- a genuine per-station counter, not a trivial day
# index, and the station-specific analogue of the blocked nationwide
# "Klimaindikator Niedrigwassertage" (docs/niwis_reference.md 8.3).
# Requires BOTH a reference period AND an interval simultaneously --
# unlike every quantity above, which needs at most one of the two.
# Discharge-only; no SumD/SumV catalog entry exists for water_level.
HYDRO_TO_NIWIS_SUM_QUANTITY={"sum_d":"SumD Zeitfenster","sum_v":"SumV Zeitfenster"}
SUM_MEASUREMENT_TYPES=frozenset({"discharge"})

# Federal-waterway navigation indicators (Sprint 7 Group E). Water_level
# only, and narrowly applicable even then: LIVE-VERIFIED empty/error at a
# regular (non-waterway) station, but real data at Kaub
# (DESM_DEXX25700100, a genuine Rhine federal-waterway gauge: "unterhalb",
# 18.0 days). No station attribute distinguishes "is this a
# Bundeswasserstraße gauge" ahead of time, so both are fetched
# unconditionally for every water_level station and degrade to
# unavailable elsewhere, like every other type-gated quantity. Neither
# needs a reference period or interval -- same param-less call shape as
# official_development_7d.
HYDRO_TO_NIWIS_BELOW_GLW_QUANTITY={"water_level":"unter GlW"}
DAYS_BELOW_GLW_NIWIS_NAME="Tage unter GlWRNW/BWu aktueller Tag"
WATERWAY_INDICATOR_MEASUREMENT_TYPES=frozenset({"water_level"})

# Groundwater depth below ground surface (Sprint 7 Group F). Uses NIWIS's
# own endpoint (30-day interval, newest valid value in the window) rather
# than computing elevation_ground - value locally: a live test station had
# elevation_ground=null while this endpoint still returned real values for
# it. Groundwater_level only.
HYDRO_TO_NIWIS_DEPTH_BELOW_GROUND_QUANTITY={"groundwater_level":"m unter Geländeoberkante"}
DEPTH_BELOW_GROUND_MEASUREMENT_TYPES=frozenset({"groundwater_level"})

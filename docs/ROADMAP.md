# Hydro Monitor Roadmap

## Vision

Hydro Monitor aims to become the leading hydrology platform for Home Assistant.

The long-term goal is not merely to expose measurements from public providers, but to provide meaningful interpretation, statistics and insights while remaining provider-independent.

---

# Development Principles

The project follows four guiding principles:

1. Provider independence
2. Scientific correctness
3. Native Home Assistant integration
4. Extensibility

Whenever possible, official provider calculations should be preferred over locally calculated values.

Hydro Monitor calculations should complement—not replace—official hydrological information.

---

# Current Status

## Version 0.3.x

Current milestone:

- NIWIS provider
- Station discovery
- Home Assistant location support
- Device model
- Entity model
- Diagnostics
- System Health
- Translation framework
- Derived quantity discovery
- API exploration tooling

Current maturity:

Alpha

---

# Version 0.4 – Hydrology Foundation

Goal:

Introduce the Hydrology Engine and expose the most valuable official hydrological indicators.

Major work packages:

## Hydrology Engine

- provider-independent calculation models
- HydroDerivedValue
- HydroClassification
- HydroQuality
- HydroTimeSeries

## Official NIWIS indicators

Priority:

★★★★★

- MQ
- MNQ
- MW
- MNW
- NM7Q
- NM30Q
- LFI

## Official classifications

★★★★★

- Low-water class
- Water-level class
- Groundwater class
- Spring-discharge class

## Trend information

★★★★☆

- Development over last 7 days
- Relative change
- Trend direction

Deliverable:

Hydro Monitor becomes more than a measurement integration.

---

# Version 0.5 – Hydrological Interpretation

Goal:

Provide historical context.

Major work packages:

## Historical comparison

★★★★★

- Historical median
- Historical minimum
- Historical maximum

## Percentiles

★★★★★

- Deciles
- Dynamic thresholds
- Static thresholds

## Dashboard support

★★★★☆

- Comparison cards
- Trend cards
- Historical reference graphs

Deliverable:

Users understand whether a measurement is normal or exceptional.

---

# Version 0.6 – Hydrological Intelligence

Goal:

Generate meaningful interpretations.

Major work packages:

## Hydrology Engine

- Insights
- Status assessment
- Trend interpretation

## Insight examples

Current discharge is 18% below the long-term average.

Groundwater level is stable.

Low-water conditions continue to intensify.

Recovery has started.

## Binary Sensors

- Low water
- Extreme low water
- Recovery
- Below threshold

Deliverable:

Hydro Monitor starts explaining hydrological conditions.

---

# Version 0.7 – Visualization

Goal:

Best-in-class dashboards.

Potential components:

- History comparison
- Decile band
- Median curve
- Threshold visualization
- Station overview
- Multi-station comparison
- Basin overview

Deliverable:

Interactive hydrological dashboards.

---

# Version 0.8 – Multi Provider Platform

Goal:

Support additional providers.

Status: started. The provider interface exists (`providers/base.py`, see
`docs/ARCHITECTURE.md`) and NIWIS and PEGELONLINE run through it
(`docs/pegelonline_reference.md`). HyDAS, the nationwide REST API standard of
the German states, is deferred until a state implements it or PEGELONLINE's
implementation leaves beta (watch `https://hydrodaten-api.mhwz.de/reals`).

Candidates are evaluated in "Provider candidates" below.

Provider support should require only:

- API Client
- Mapper

Everything else should already exist.

Deliverable:

Provider-independent hydrology platform.

## Provider candidates

Evaluated on 2026-10-23. **Verified** means queried live that day; **reported**
means taken from a web search or documentation and not checked. Nothing here is
decided: it is the shortlist to build the next provider from.

What a provider needs to be worth integrating:

- an open API without key or account (the integration is open source, so a
  per-user account cannot be shipped),
- a licence that allows use in an open-source integration,
- coordinates and a current value per station (the station list is sorted by
  distance),
- a fit to the four measurement types; groundwater and springs are the rare
  ones (only NIWIS has them today),
- a stable service (versioning policy, no beta).

Every provider outside Germany also changes the project's scope: the README and
`hacs.json` (`country: ["DE"]`) say "Germany only", and licences that require
attribution (see below) must be shown to the user.

### Germany

| Candidate | Status |
|---|---|
| **HyDAS of the states** | Standard of the German states. No state serves it yet; the only live implementation is PEGELONLINE's beta (`hydrodaten-api.mhwz.de/reals`, verified). Watched by the weekly task. Would unlock many states, and the standard already models groundwater and springs. **First choice once a state goes live.** |
| LHP (hochwasserzentralen.de) | Aggregates the gauges of all 16 states, but only through an undocumented JSON interface that third parties use, with no stated licence (the rights lie with the states). Run by the same group as HyDAS, which replaces it. **Not recommended.** |
| NLWKN Lower Saxony, Grundwasserstandonline | JSON web service, own licence "Open Data NLWKN" (reported). Documentation embeds an API key and warns of swapped coordinates. Whether NIWIS already covers it: not checked. |
| Other states (NRW, Bayern HND, BW, Sachsen, ...) | One client each, mixed access and licences. Not checked; wait for HyDAS. |

### Neighbours and further abroad

| Candidate | What was verified | Open points |
|---|---|---|
| **France: Hub'Eau** | Hydrometry: 4195 stations in service, level (H) and discharge (Q) with timestamps and coordinates (verified). Groundwater: 23 355 stations (list verified). REST API, no key. | Licence not confirmed (probably Licence Ouverte). Latest groundwater readings not verified (the first station returned none). Version 1 of the hydrometry API was shut down on 2025-05-05. **Best fit: the only open REST API covering surface water and groundwater.** |
| **UK: Environment Agency** | 4230 level and 351 flow stations, JSON, coordinates, Open Government Licence v3 (verified). | The service calls itself "Beta service" (version 0.9). Groundwater uses a different API (not checked). |
| **Switzerland: BAFU** | Official route is LINDAS (SPARQL, `lindas.admin.ch/query`, graph `foen/hydro`): a river cube with station, measurement time, water level, discharge, water temperature, danger level (198 observations) and a lake cube, updated every 10 minutes (verified). The old direct files (`hydroweb.xml`, GeoJSON) answer 404. Terms (AGB 2019, read): commercial and non-commercial use allowed, source citation recommended, polling at most every 10 minutes, unchecked data without guarantee. | SPARQL instead of REST. No groundwater. The AGB are written for the account-based download server; the BAFU page names them for its data, LINDAS' own terms were not read. The third-party API `api.existenz.ch` works but is a private, non-commercial service without availability guarantee: **not a basis**. One Swiss gauge (Basel-Rheinhalle) already comes through PEGELONLINE. |
| **Austria: federal OGC API** (BMLUK, "Downloaddienst Hydrographie Österreich") | Found via the data.gv.at dataset "Aktuelle Pegelstände Österreich" (licence CC BY 4.0). Modern OGC API Features, GeoJSON points, no key, no rate-limit headers: `https://gis.lfrz.gv.at/api/geodata/i000501/ogc/features/v1` (all verified). Collections: `pegel_aktuell` (300 gauges: 266 discharge in m³/s, 28 water levels in cm, 4 in m ü.A; no station has both; values 1.6 to 3 hours old; 2 without a timestamp), `grundwasser_aktuell` (234 stations, daily values), `messstellen_owf` (798 surface-water stations), `messstellen_gw`, `niederschlag_aktuell`, and `messstellen_qu` (97 **spring stations, but no current spring values**). Fields: `hzbnr` (station number), `messstelle`, `wert`, `einheit`, `zeitpunkt`, `parameter`, `gewaesser`, `hydrodienst`, link to the state's own portal. | The data come from the states' services and some hydropower operators (Tirol, Salzburg, TIWAG, VHP, ...), so the data owners differ; the attribution wording still has to be settled. Values lag by about two hours. No springs (stations only). Water level and discharge are separate features per station. The service's own terms and stability (no versioning information seen) are not documented in the collection. Also reported: state portals Tirol `hydro.tirol.gv.at` (over 900 stations incl. groundwater and springs, every 15 minutes) and Upper Austria `hydro.ooe.gv.at`, with no API found. Federal eHYD (checked archive data as CSV) stays the source for history. PEGELONLINE has 9 Austrian Danube gauges (viadonau), but only Achleiten has coordinates. |
| Poland: IMGW | 913 stations in one JSON file with level, discharge, coordinates and alarm levels (verified). | Licence not checked; some discharge values are months old. |
| Netherlands (Rijkswaterstaat), Sweden (SMHI), Flanders | A quick probe failed (404, 503, 500). | **Not verified**: the real endpoints need proper research. |
| USA: USGS | Reachable, JSON (verified). | Out of region; only if the project goes worldwide. |

### Suggested order

1. HyDAS of the states, as soon as one goes live (nothing to build before).
2. France (Hub'Eau): closest to the data model, with surface water and groundwater in
   one open REST API. Verify the licence and the latest groundwater readings first.
3. Austria (federal OGC API): discharge, water level and groundwater for the whole
   country in one documented service. Settle the attribution wording first.
4. UK (Environment Agency), then Switzerland (LINDAS).

Before building any of them: decide the scope question (Germany only or not),
read the licence in full, and capture real responses as fixtures with a
discovery tool like `tools/pegelonline_discovery.py`.

---

# Long-Term Ideas

Potential future features include:

## Hydrological Insights

Human-readable explanations.

## Basin comparison

Compare nearby stations.

## River progression

Upstream / downstream comparison.

## Drought monitoring

Automatic drought assessment.

## Flood monitoring

Automatic flood assessment.

## Notifications

Hydrological events.

## Climate indicators

Long-term hydrological trends.

## Dashboard widgets

Dedicated Hydro Monitor Lovelace cards.

---

# Prioritisation

## Critical

- Core architecture
- Hydrology Engine
- Official indicators

## High

- Historical comparison
- Trend interpretation
- Dashboard support

## Medium

- Visualisation
- Additional providers

## Low

- Experimental analytics
- AI-generated summaries

---

# Definition of Done

A feature is considered complete when:

- Architecture documented
- Unit tests implemented
- Home Assistant diagnostics supported
- Translation keys added
- Documentation updated
- No provider-specific logic leaks into entities

---

# Release Philosophy

Alpha

Architecture and API evolve quickly.

Beta

Stable entity model.

Stable configuration flow.

Stable unique IDs.

Version 1.0

Provider-independent hydrology platform.

Backward-compatible entity model.

Comprehensive documentation.

Multiple supported providers.

Complete Hydrology Engine.

---

# Success Criteria

Hydro Monitor should eventually provide:

- Accurate measurements
- Official hydrological indicators
- Historical context
- Trend analysis
- Hydrological interpretation
- Beautiful dashboards
- Provider independence
- Excellent documentation
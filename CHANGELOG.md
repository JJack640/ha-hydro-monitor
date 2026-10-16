# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## Unreleased

Adapts to a restructuring of the NIWIS API (found 2026-10-16). Between
2026-08-17 and 2026-10-16 NIWIS renamed, moved or removed several derived
quantities without notice (there is no changelog or API description), which
left the low-water class and a few statistics permanently unavailable in
v0.3.0-beta2. Details: `docs/niwis_reference.md` §7.18.

### Fixed

- **Low-water class** (all measurement types): NIWIS removed the per-station
  "… Niedrigwasserklasse aktueller Tag" quantities. The class now comes from
  NIWIS's own map-classification endpoint (one cached list per measurement
  type, shared between devices) using NIWIS's default `DYNAMISCH`
  classification. The `raw_value` attribute now carries NIWIS's enum
  (`EXTREM_NIEDRIG`, `SEHR_NIEDRIG`, `NIEDRIG`, `KEIN_NIEDRIGWASSER`,
  `KEINE_DATEN`) instead of the former German label ("extrem niedrig");
  the sensor states themselves are unchanged. Stations without current data
  (`KEINE_DATEN`) stay unavailable, as on NIWIS's own map.
- **NM7Q / NM30Q** (and their `occurred_from`/`occurred_to` attributes):
  now one request each on NIWIS's category endpoint instead of four requests
  in total; the plain value and the date range come from the same result.
- **SumD / SumV**, **days below GlW**, **depth below ground**: adjusted to the
  new NIWIS names/endpoints (`SumD`/`SumV`, `Tage unter GlW`, a plain
  parameter-less `m unter Geländeoberkante`).

### Added

- `python -m tools.niwis_contract_check`: compares what the integration
  requests with what NIWIS currently offers and exits non-zero on drift, so
  an API change like this one is noticed immediately.

---

## v0.3.0-beta2 (2026-08-09)

Completes the official NIWIS derived-quantity catalogue (43/43 quantities
now implemented or explicitly deferred/blocked with documented reasoning)
and improves discoverability of the many official-statistic sensors added
along the way.

### Added

- 18 previously-untouched NIWIS derived quantities ("Sprint 7"):
  - Historical calendar-day envelope: min/median/max discharge and median
    water level for today's exact calendar day, reference period
    1991-2020, disabled by default
  - Reference-period NQ, Median Q (discharge) and NW, Median W (water
    level), disabled by default
  - NM7Q/NM30Q "mit Datum": the date range each lowest-discharge extreme
    occurred in, exposed as `occurred_from`/`occurred_to` attributes on
    the existing NM7Q/NM30Q sensors
  - SumD/SumV: accumulated low-water days and discharge deficit volume
    over the last 30 days (discharge only), disabled by default
  - Waterway navigation indicators: below GlW, days below GlW/RWN/BWu,
    for federal waterway gauges (water level only), disabled by default
  - Groundwater depth below ground surface (Flurabstand), disabled by
    default
- A plain-language glossary (`sensor_glossary.py`), surfaced as a
  localized `description` attribute on every official NIWIS sensor, since
  their names mirror NIWIS's own hydrological abbreviations (MQ, GlW,
  ...) and Home Assistant has no per-entity tooltip mechanism
- Historical range comparison in the example dashboards' history graphs:
  discharge and water level now plot the actual value alongside NIWIS's
  calendar-day envelope (or, where NIWIS has no calendar-day min/max, the
  rolling 30-day minimum/maximum); groundwater level and spring discharge
  use the rolling 30-day minimum/maximum

### Fixed

- A naming collision between the new NQ/NW sensors and the pre-existing
  `historical_low_discharge`/`historical_low_water_level` station-metadata
  sensors, which shared the exact same translated label

### Documented

- README's "Available Sensors" table expanded to cover every sensor added
  across Sprints 1-7

## v0.3.0-beta1 (2026-08-07)

First beta release: Phase 2-6 of the technical roadmap are complete
(implemented or explicitly deferred/blocked with documented reasoning), the
project is moving from active feature development into stabilization, and
this release adds the metadata required for official HACS listing.

### Added

- Four new `%`-of-mean comparison sensors: `percent_of_mq`/`mnq` (discharge),
  `percent_of_mw`/`mnw` (water level), disabled by default
- Example Lovelace dashboards (`docs/examples/`): one view per measurement
  type plus a multi-station comparison view, in English and German
- `codeowners` in `manifest.json` (was empty)

### Changed

- Device name/model text and the config entry title (e.g. "Inkofen –
  Abfluss") now follow Home Assistant's configured instance language
  instead of always being English, via a new shared
  `custom_components/hydro_monitor/localization.py` module
- Corrected documentation: NIWIS is a nationwide German service, not
  Bavaria-only as earlier revisions of `docs/niwis_reference.md` stated

## v0.3.0-alpha4 (2026-08-07)

### Added

- Official NIWIS low-water classification sensor (`Niedrigwasserklasse`) for all four measurement types, failing independently of the primary observation
- Official static and dynamic low-water classification boundary sensors (disabled by default), with dynamic boundaries cached per calendar day
- Official NIWIS 7-day development sensor for discharge and water level, distinct from the existing locally-calculated 7-day trend
- Official historical statistics MQ, MNQ, NM7Q, NM30Q (discharge) and MW, MNW (water level), as disabled-by-default sensors
- Manual station search in the config flow: search all stations nationwide by name, not just the nearest 25
- 11 official NIWIS decile boundary sensors (P0-P100) for discharge and water level, disabled by default

### Changed

- Low-water classification sensor upgraded to a proper `SensorDeviceClass.ENUM`, now that the full 4-value label domain is confirmed
- Static and dynamic low-water boundary sensors now display 2 decimal places instead of raw floating-point precision
- `as_float()` now rejects the literal string `"NaN"` returned by NIWIS for poor-quality results

### Fixed

- Corrected the NM7Q/NM30Q historical-statistics interval: both need a flat 30-day window rather than a window matching each quantity's own name, live-verified against the real API

### Documented

- LFI (Low Flow Index) is blocked and deferred: live-tested against 5 discharge stations, all failed with NIWIS's own "cannot be calculated for this station" error
- Both NIWIS climate-indicator endpoints (low-water days, monthly mean deviations) are blocked and deferred: live-tested and confirmed to return nationwide, non-station-specific data with no reliable way to attribute a configured station to a river basin

## v0.3.0-alpha3 (2026-07-24)

### Added

- Extended NIWIS station metadata: waterbody and waterbody code (GKZ), river kilometre, catchment area, gauge zero elevation, ground elevation, elevation reference system, locality, station type, hydrogeological region and region code, operator, institution, source and licence information, historical NQ/NW values and dates
- Reproducible NIWIS discovery and inventory tooling (station catalogue inventory, field/schema analysis, sampled time-series data, data-quality statistics, derived-quantity discovery and endpoint probing)
- Comprehensive NIWIS provider technical reference (`docs/niwis_reference.md`)

### Changed

- Station metadata and changing observations now use separate entity classes (`HydroObservationSensor`, `HydroStationSensor`) for cleaner device pages
- Readable licence names, correct river-kilometre unit, improved numerical precision, stable entity unique IDs
- Only metadata actually available for a station is exposed as an entity

## v0.3.0-alpha2 (2026-07-21)

### Added

- Home Assistant Diagnostics support
- Home Assistant System Health support
- Device separation by measurement type
- Improved localization (German and English)
- Additional diagnostic entities
- Extensive unit test coverage

### Changed

- Complete code quality review
- Refactored Config Flow
- Improved type hints and documentation
- Improved mapper performance
- Improved NIWIS catalog cache handling
- Improved sensor implementation
- Improved translation handling
- Improved runtime robustness

### Fixed

- Config Flow compatibility with Home Assistant 2026.7
- Device merging when using multiple measurement types
- Various Home Assistant style and quality issues

## [0.3.0-alpha1]

### Added

- Native Home Assistant Config Flow
- Automatic station discovery using the Home Assistant location
- Provider abstraction for future hydrological data sources
- NIWIS provider implementation
- Groundwater level sensors
- Water level sensors
- River discharge sensors
- Spring discharge sensors
- 1-day trend sensor
- 7-day trend sensor
- Water level trend enum sensor
- 30-day minimum sensor
- 30-day maximum sensor
- Last observation sensor
- Measurement age sensor
- Dynamic trend icons
- Native Home Assistant diagnostics support
- Native Home Assistant system health support
- Full English and German translations
- HACS-compatible repository structure
- GitHub Actions CI
- Unit tests for:
  - Station discovery
  - Home Assistant location
  - NIWIS mapper
  - Sensor helpers
  - Diagnostics

### Changed

- Improved trend calculation for missing historical measurements
- Improved handling of invalid NIWIS placeholder values
- Improved diagnostics output
- Improved README documentation
- Improved localization using translation keys

### Fixed

- Correct handling of historical data gaps
- Correct trend calculation using previous available measurements
- Fixed measurement restoration behaviour
- Fixed translation handling for enum sensors
- Fixed sensor metadata for Home Assistant diagnostics
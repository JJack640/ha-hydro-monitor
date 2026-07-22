# Hydro Monitor Architecture

## Overview

Hydro Monitor is a Home Assistant integration for monitoring and interpreting hydrological data from public data providers.

The project is designed as a provider-independent hydrology platform rather than as a direct wrapper around a single API.

NIWIS is currently the first supported provider. Future providers should integrate through the same internal data models and interfaces without requiring provider-specific logic in Home Assistant entities.

---

## Design Goals

Hydro Monitor follows these architectural goals:

- Native integration with Home Assistant
- Clear separation between providers and hydrological logic
- Provider-independent data models
- Reusable calculations and classifications
- Transparent distinction between official provider values and Hydro Monitor calculations
- Strong typing and testability
- Extensibility for additional providers and measurement types
- Privacy-conscious diagnostics
- Graceful handling of missing, invalid or stale data
- Stable entity and device identifiers

---

## Current Architecture

The current data flow is:

```text
Public hydrological API
        │
        ▼
Provider API client
        │
        ▼
Provider mapper
        │
        ▼
HydroStation / HydroObservation
        │
        ▼
DataUpdateCoordinator
        │
        ▼
Home Assistant entities
```

For NIWIS, this currently means:

```text
NIWIS API
        │
        ▼
NiwisClient
        │
        ▼
NIWIS Mapper
        │
        ▼
HydroStation / HydroObservation
        │
        ▼
HydroMonitorCoordinator
        │
        ▼
Sensor entities
```

The integration already separates provider-specific API access from Home Assistant entities, but derived hydrological results still require a normalized provider-independent layer.

---

## Target Architecture

The target architecture introduces a provider-independent Hydrology Engine:

```text
                         Home Assistant
                               │
                               ▼
                         Hydro Monitor
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
       Provider Layer                   Hydrology Engine
              │                                 │
     ┌────────┼────────┐              ┌─────────┼─────────┐
     │        │        │              │         │         │
   NIWIS   Provider 2  ...         Statistics Trends Classification
                                                │
                                                ▼
                                             Insights
              │                                 │
              └────────────────┬────────────────┘
                               ▼
                         Entity Factory
                               │
              ┌────────────────┼────────────────┐
              │                │                │
            Sensors       Diagnostics      Dashboards
```

The Hydrology Engine must not depend on NIWIS-specific field names or endpoints.

---

## Architectural Layers

### 1. Provider Layer

The provider layer communicates with external hydrological data services.

Responsibilities:

- HTTP communication
- Provider-specific endpoints and query parameters
- Provider-specific authentication, where required
- Provider-specific error handling
- Parsing raw API responses
- Mapping provider data into Hydro Monitor models
- Exposing official provider calculations and classifications
- Preserving provider attribution and reference parameters

Provider modules must not contain Home Assistant entity logic.

Current provider structure:

```text
providers/
└── niwis/
    ├── api.py
    ├── catalog.py
    ├── const.py
    └── mapper.py
```

Possible future providers:

```text
providers/
├── niwis/
├── pegelonline/
├── bafu/
├── rijkswaterstaat/
└── ...
```

Adding a provider should ideally require only:

- an API client,
- provider-specific constants,
- response mappers,
- provider-specific tests.

The entity layer and Hydrology Engine should remain unchanged.

---

### 2. Core Models

Core models represent hydrological data independently of its source.

Current models:

- `HydroMeasurementType`
- `HydroStation`
- `HydroObservation`

These models must not contain provider-specific field names such as `messstelleNr`, `messwert` or `abgeleiteteGroesse`.

Current example:

```python
@dataclass(frozen=True, slots=True)
class HydroObservation:
    measurement_type: HydroMeasurementType
    value: float | None
    unit: str | None
    observed_on: date | None

    quality_flag: str | None = None
    change_1d: float | None = None
    change_7d: float | None = None
    minimum_30d: float | None = None
    maximum_30d: float | None = None
    sample_count: int = 0
```

Planned additional models include:

- `HydroDerivedValue`
- `HydroClassification`
- `HydroReferencePeriod`
- `HydroQuality`
- `HydroTimeSeries`
- `HydroThreshold`
- `HydroInsight`

---

### 3. Hydrology Engine

The Hydrology Engine contains provider-independent calculations, classifications and interpretation logic.

Planned structure:

```text
core/
└── hydrology/
    ├── calculations.py
    ├── classifications.py
    ├── derived.py
    ├── insights.py
    ├── quality.py
    ├── statistics.py
    └── trends.py
```

Responsibilities may include:

- Trend calculations
- Rolling statistics
- Data-quality assessment
- Comparison with official reference values
- Relative differences
- Percentile and decile interpretation
- Hydrological status classification
- Generation of human-readable insights

The Hydrology Engine must not:

- make API requests,
- import provider-specific modules,
- depend on Home Assistant entities,
- silently replace official provider values.

It receives normalized models and returns normalized results.

---

### 4. Derived Result Layer

NIWIS currently advertises 43 derived quantities across:

- discharge,
- water level,
- groundwater level,
- spring discharge.

The API provides several result families:

- numeric single values,
- category values,
- numeric time series,
- static classification thresholds,
- dynamic classification thresholds,
- aggregated climate indicators.

Hydro Monitor should not implement 43 independent code paths. Provider responses should instead be normalized into a small set of reusable result models.

A possible numeric result model:

```python
@dataclass(frozen=True, slots=True)
class HydroDerivedValue:
    key: str
    value: float | None
    unit: str | None
    source: str
    reference_period: HydroReferencePeriod | None
    observed_on: date | None
    quality: HydroQuality | None
```

A possible category model:

```python
@dataclass(frozen=True, slots=True)
class HydroClassification:
    key: str
    category: str | None
    source: str
    reference_period: HydroReferencePeriod | None
    observed_on: date | None
    quality: HydroQuality | None
```

A possible time-series model:

```python
@dataclass(frozen=True, slots=True)
class HydroTimeSeries:
    key: str
    values: tuple[HydroTimeSeriesPoint, ...]
    unit: str | None
    source: str
    reference_period: HydroReferencePeriod | None
    quality: HydroQuality | None
```

The exact models should be finalized only after the response structures of all derived NIWIS calculations have been inventoried.

---

### 5. Coordinator Layer

The coordinator manages updates for each Home Assistant config entry.

Responsibilities:

- Fetching provider data
- Updating current observations
- Fetching selected official derived values
- Coordinating refresh intervals
- Converting provider failures into Home Assistant update failures
- Making normalized results available to entities
- Tracking the last successful update

Each config entry currently represents one combination of:

```text
provider + station + measurement type
```

Examples:

```text
NIWIS + Inkofen + discharge
NIWIS + Inkofen + water level
```

This separation prevents sensors from different measurement types from being merged into one device.

Future coordinator runtime data may contain:

```text
station
current observation
derived values
classifications
reference values
data quality
time series
```

---

### 6. Entity Layer

The entity layer exposes normalized hydrological data to Home Assistant.

Responsibilities:

- Entity descriptions
- Translation keys
- Native units
- Device classes
- State classes
- Icons
- Device information
- Entity categories
- User-facing attributes

Entities must not:

- call provider APIs,
- parse provider responses,
- duplicate hydrological calculations,
- contain provider-specific endpoint logic.

Unique IDs should contain:

```text
provider
station ID
measurement type
entity key
```

Example:

```text
niwis:DESM_DEBY16607001:discharge:change_7d
```

Device identifiers should contain:

```text
provider
station ID
measurement type
```

Example:

```text
niwis:DESM_DEBY16607001:discharge
```

This ensures that discharge and water-level entities from the same physical station remain separate Home Assistant devices.

---

### 7. Entity Factory

As the number of official indicators grows, entities should be generated from reusable descriptions rather than implemented individually.

Potential entity groups:

- Primary measurement entities
- Hydro Monitor calculated statistics
- Official provider indicators
- Official provider classifications
- Data-quality diagnostics
- Reference values
- Threshold values

The Entity Factory should decide which entities apply to a particular:

```text
provider + measurement type + available capability
```

An entity should only be created when:

- the provider supports the value,
- the station supports the calculation,
- the result can be interpreted reliably,
- the entity has clear user value.

---

### 8. Diagnostics and System Health

Hydro Monitor supports native Home Assistant diagnostics and System Health.

Diagnostics may include:

- Integration version
- Provider
- Station metadata
- Current observation
- Trend and statistical values
- Derived-result metadata
- Reference periods
- Data-quality information
- Coordinator state
- Update interval
- Last update result

Diagnostics must exclude sensitive Home Assistant location data.

System Health currently reports:

- Configured entries
- Loaded entries
- Configured stations
- Providers
- Last update status
- Update interval
- Latest observation

Future System Health information may include:

- Availability of provider APIs
- Derived-result update status
- Number of failed calculations
- Age of cached reference data

---

## Official and Calculated Values

Hydro Monitor distinguishes explicitly between official provider data and locally calculated values.

### Official Provider Values

Official values are supplied directly by a data provider.

NIWIS examples include:

- MQ
- MNQ
- MW
- MNW
- NM7Q
- NM30Q
- LFI
- Low-water classifications
- Static classification thresholds
- Dynamic classification thresholds
- Deciles
- Groundwater depth below ground level
- Climate indicators

Official values must preserve:

- Provider attribution
- Calculation name
- Reference period
- Year definition
- Time interval
- Quality state
- Provider error messages

### Hydro Monitor Calculations

Hydro Monitor currently calculates values such as:

- 1-day change
- 7-day change
- 30-day minimum
- 30-day maximum
- Measurement age
- Trend direction
- Trend strength

Possible future calculations include:

- Relative difference to MQ or median
- Position within an official threshold range
- Data availability percentage
- Number of consecutive rising or falling measurements
- Difference to an official low-water threshold

Calculated values must be documented clearly and must not be presented as official provider values.

---

## Reference Periods

Many official calculations require a historical reference period.

A reference period may include:

- Year definition
- Start year
- End year

Supported NIWIS year definitions include:

- `KALENDERJAHR`
- `HYDROLOGISCHESJAHR`
- `WASSERHAUSHALTSJAHR`

Reference-period information must be part of the normalized result and should be visible in entity attributes or diagnostics.

Hydro Monitor must not display an official statistical value without preserving the reference period used to calculate it.

---

## Data Quality

Hydrological APIs may return:

- Missing values
- Placeholder values
- Provider flags
- Incomplete time series
- Empty calculation results
- Excessive missing-data indicators
- Provider-specific calculation errors
- Stale observations

Known invalid NIWIS placeholder values include:

```text
-777
-888
-999
-9999
```

NIWIS derived calculations may also return:

```text
hatZuvieleFehlwerte
fehlermeldung
```

Hydro Monitor must:

- Exclude invalid values from local calculations
- Preserve provider flags for diagnostics
- Avoid presenting placeholders as measurements
- Detect and report stale data
- Preserve calculation errors
- Distinguish between unavailable and invalid results
- Avoid creating misleading classifications from incomplete data

A future normalized quality model may include:

```python
@dataclass(frozen=True, slots=True)
class HydroQuality:
    valid: bool
    stale: bool
    coverage_percent: float | None
    provider_flag: str | None
    excessive_missing_values: bool
    error: str | None
```

---

## Caching Strategy

Different data types require different update intervals.

Examples:

- Current observations: frequent refresh
- Station metadata: long-lived cache
- Reference-period statistics: long-lived cache
- Classification of current conditions: regular refresh
- Historic comparison curves: long-lived cache
- Climate indicators: infrequent refresh

Hydro Monitor should avoid fetching expensive historical calculations during every coordinator update.

A future caching strategy may distinguish between:

```text
observation cache
station metadata cache
reference-value cache
classification cache
historical time-series cache
```

Cache invalidation should consider:

- Provider update frequency
- Reference-period changes
- Config-entry options
- Provider errors
- Integration version changes

---

## Configuration Model

The Config Flow currently follows these steps:

1. Select a measurement type.
2. Discover nearby stations using the Home Assistant location.
3. Select a station.
4. Create one config entry for the selected station and measurement type.

The unique Config Entry ID uses:

```text
provider:station_id:measurement_type
```

Potential future options include:

- Reference-period year definition
- Reference-period start and end year
- Optional official indicators
- Optional historical comparison series
- Analysis-window length
- Data-quality thresholds
- Configurable update intervals

Provider-specific options should remain isolated from generic integration settings.

---

## Translation Strategy

Hydro Monitor uses Home Assistant translation keys.

Translated content includes:

- Config Flow labels
- Selector options
- Sensor names
- Enum states
- Error messages
- Abort reasons

Internal identifiers remain stable English keys.

Config Entry titles and device identifiers should remain understandable without depending on the current interface language.

Official provider categories should be mapped to stable internal keys before translation.

---

## Testing Strategy

The project currently contains automated tests for:

- Station discovery
- Home Assistant location handling
- NIWIS mapping
- Invalid-value filtering
- Trend calculations
- Sensor metadata
- Diagnostics

Future tests should cover:

- Config Flow behavior
- Derived-result parsing
- Numeric results
- Category results
- Time-series results
- Static and dynamic thresholds
- Reference-period handling
- Excessive missing-data responses
- Provider calculation errors
- Hydrology Engine calculations
- System Health with no loaded entries
- Entity availability when a derived result fails

Every normalized result family should have provider fixtures and provider-independent model tests.

---

## Repository Boundaries

Production integration code belongs under:

```text
custom_components/hydro_monitor/
```

Developer tools belong under:

```text
tools/
```

Generated discovery output belongs outside the production package:

```text
niwis_inventory/
```

Documentation belongs under:

```text
docs/
```

The production integration package must not contain:

- Generated API inventories
- Developer-only scripts
- Large historical datasets
- Temporary API responses
- Discovery reports

Representative anonymized fixtures may be stored under `tests/fixtures/` when required for automated tests.

---

## Documentation Structure

The project documentation is divided by audience:

```text
README.md
```

For users and installation guidance.

```text
docs/ARCHITECTURE.md
```

For technical design and development principles.

```text
docs/ROADMAP.md
```

For version planning and feature priorities.

Possible future documents:

```text
docs/PROVIDERS.md
docs/HYDROLOGY.md
docs/DASHBOARDS.md
```

---

## Future Evolution

The intended development order is:

1. Complete NIWIS API discovery
2. Inventory all derived-result response structures
3. Normalize derived-result families
4. Introduce provider-independent hydrology models
5. Add high-value official indicators
6. Add classifications and historical context
7. Add dashboard examples and visualizations
8. Add a second provider
9. Reuse the Hydrology Engine across providers

---

## Architectural Principles

All future changes should follow these principles:

1. Prefer official provider calculations when available.
2. Keep provider code separate from Home Assistant entity code.
3. Do not duplicate hydrological calculation logic.
4. Normalize provider responses before exposing entities.
5. Preserve provenance and reference periods.
6. Treat missing and invalid data explicitly.
7. Avoid creating entities without clear user value.
8. Prefer reusable result models over endpoint-specific implementations.
9. Keep diagnostics useful but privacy-conscious.
10. Maintain backward-compatible unique IDs whenever possible.
11. Do not fetch expensive historical calculations on every update.
12. Keep user-facing entities stable even if provider APIs change.
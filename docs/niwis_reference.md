# Hydro Monitor Technical Reference — NIWIS Provider

**Document version:** 0.3.0-alpha  
**Last updated:** July 2026  
**Status:** Living technical reference

This document reflects the Hydro Monitor implementation and NIWIS discovery
results available for release `0.3.0-alpha`.

> Technical reference for the NIWIS provider used by Hydro Monitor.
>
> This document captures the technical knowledge gathered during the design and
> implementation of the NIWIS provider. It documents the public API, field
> mappings, observed API behaviour, reverse engineering findings, implementation
> decisions and future development strategy.
>
> Unlike the project README, this document is intended for developers working on
> Hydro Monitor. It explains not only *how* the provider is implemented, but
> also *why* certain architectural decisions were made.

## Table of Contents

1. [Introduction](#1-introduction)
2. [NIWIS Provider Architecture](#2-niwis-provider-architecture)
3. [Station Catalogue and Metadata](#3-station-catalogue-and-metadata)
4. [Observation Data and Processing](#4-observation-data-and-processing)
5. [Data Quality and Measurement-Type Characteristics](#5-data-quality-and-measurement-type-characteristics)
6. [Reverse Engineering the NIWIS API](#6-reverse-engineering-the-niwis-api)
7. [Official NIWIS Derived Quantities](#7-official-niwis-derived-quantities)
8. [Climate Indicators](#8-climate-indicators)
9. [Architecture Decision Record](#9-architecture-decision-record)
10. [Development Roadmap](#10-development-roadmap)
11. [Known Limitations and Open Questions](#11-known-limitations-and-open-questions)
12. [Document History](#12-document-history)

### Planned appendices

- Appendix A — NIWIS Field Dictionary
- Appendix B — API Endpoint Reference
- Appendix C — Derived Quantity Catalogue

---

# 1. Introduction

## Purpose

Hydro Monitor is designed as a provider-independent hydrological monitoring
integration for Home Assistant.

The Bavarian NIWIS (Niedrigwasser-Informationssystem) is the first supported
provider and therefore serves as the reference implementation for the project's
architecture.

Although the current implementation focuses exclusively on NIWIS, the overall
design deliberately separates provider-specific logic from the provider-neutral
core models used throughout the integration.

As a result, future providers (for example other German federal states or
European hydrological services) should be able to integrate into Hydro Monitor
without requiring changes to the Home Assistant entity layer.

This document serves as the technical reference for the NIWIS provider.

It documents

- the structure of the public NIWIS API,
- provider architecture,
- station catalogue behaviour,
- metadata mapping,
- observation processing,
- quality handling,
- reverse engineering findings,
- discovered derived calculations,
- implementation decisions,
- future development plans.

The intention is that a developer should be able to understand the complete
provider implementation without needing to rediscover API behaviour through
experimentation.

---

## Philosophy

Hydrological data differs fundamentally from many Home Assistant integrations.

Most Home Assistant integrations expose the current value of a device.

Hydrological monitoring is different.

A single observation only becomes meaningful once it is interpreted within its
hydrological context.

Examples include

- comparison with previous observations,
- comparison with long-term statistics,
- historical low-water events,
- catchment characteristics,
- groundwater region,
- derived hydrological indicators.

Hydro Monitor therefore separates

- raw observations,
- station metadata,
- locally calculated information,
- official NIWIS derived quantities.

Keeping these concepts separate simplifies future development while avoiding the
mixing of measured values with interpreted values.

---

## Scope

This document intentionally goes beyond the official NIWIS documentation.

During development the complete public API was systematically explored.

Besides the officially documented endpoints, numerous additional characteristics
were analysed, including

- station catalogue structure,
- metadata availability,
- quality flags,
- placeholder values,
- measurement type differences,
- derived quantity endpoints,
- endpoint parameter requirements,
- response schemas,
- climate indicator endpoints.

Much of this information is not documented elsewhere.

This reference therefore serves as the project's long-term technical knowledge
base.

---

## Intended Audience

This document is intended for

- Hydro Monitor maintainers,
- future project contributors,
- developers implementing new providers,
- developers extending the NIWIS provider,
- reviewers performing architectural changes.

It is **not** intended as end-user documentation.

Users should refer to the project README.

---

## Relationship to other project documentation

| Document | Purpose |
|----------|---------|
| README.md | User documentation |
| architecture.md | Overall project architecture |
| niwis_reference.md | Complete NIWIS technical reference |
| CHANGELOG.md | Project history |

---

## Current implementation status

At the time of writing this document, Hydro Monitor supports

- provider-independent core models,
- station discovery,
- Home Assistant config flow,
- complete station metadata mapping,
- observation processing,
- trend calculation,
- rolling statistics,
- diagnostics,
- system health,
- comprehensive automated tests.

Official NIWIS derived quantities have already been analysed and inventoried,
but are intentionally implemented in a later development phase.

This staged approach keeps the integration stable while establishing a solid
foundation for future hydrological intelligence.

---

## Design Goals

The long-term objectives of Hydro Monitor are

1. provider independence,
2. high data quality,
3. transparent processing,
4. maintainable architecture,
5. comprehensive metadata support,
6. hydrological correctness,
7. first-class Home Assistant integration.

Whenever these goals conflict, correctness and maintainability take precedence
over implementation convenience.

---

# 2. NIWIS Provider Architecture

## Overview

The NIWIS provider is intentionally separated into several independent layers.

Each layer has a single responsibility and communicates only through
provider-independent models.

```text
                ┌─────────────────────────────┐
                │        NIWIS REST API       │
                └──────────────┬──────────────┘
                               │
                               ▼
                    providers/niwis/api.py
                               │
                               ▼
                 providers/niwis/catalog.py
                               │
                               ▼
                 providers/niwis/mapper.py
                               │
             ┌─────────────────┴─────────────────┐
             ▼                                   ▼
      HydroStation                      HydroObservation
             │                                   │
             └─────────────────┬─────────────────┘
                               ▼
                 HydroMonitorCoordinator
                               │
         ┌─────────────────────┴─────────────────────┐
         ▼                                           ▼
HydroObservationSensor                     HydroStationSensor
                               │
                               ▼
                      Home Assistant
```

The architecture deliberately isolates provider-specific logic from the Home
Assistant integration.

Only the NIWIS provider knows the original API payload.

All remaining layers work exclusively with provider-independent models.

---

## Design Principles

The provider architecture follows several principles.

### Separation of responsibilities

Each module has exactly one primary responsibility.

| Module | Responsibility |
|---------|----------------|
| api.py | Communication with the NIWIS REST API |
| catalog.py | Station catalogue handling |
| mapper.py | Conversion of NIWIS payloads into core models |
| coordinator.py | Update scheduling |
| sensor.py | Home Assistant entities |

No module should perform responsibilities belonging to another layer.

---

### Provider independence

The Home Assistant entity layer never accesses NIWIS payloads directly.

Instead it consumes

- `HydroStation`
- `HydroObservation`

This abstraction makes it possible to support additional providers in the
future without changing entity implementations.

The goal is that every provider produces the same internal models.

---

### Defensive mapping

The NIWIS API cannot be assumed to provide complete data.

Consequently every mapper follows these principles:

- optional fields remain `None`
- numeric parsing is defensive
- invalid dates are ignored
- unknown metadata is preserved
- unknown quality flags are preserved
- placeholder values never become observations

The integration always prefers partial but trustworthy data over guessed values.

---

### Home Assistant independence

Provider code intentionally contains no Home Assistant entity logic.

Provider modules should be reusable outside Home Assistant.

The Home Assistant-specific implementation begins only with

- coordinator.py
- sensor.py
- diagnostics.py
- system_health.py

This keeps provider logic easy to test.

---

## Provider directory structure

The current provider implementation is organised as follows.

```text
providers/
└── niwis/
    ├── __init__.py
    ├── api.py
    ├── catalog.py
    ├── mapper.py
    └── const.py
```

### api.py

Responsible for

- HTTP requests
- endpoint construction
- response retrieval
- JSON decoding

This module intentionally performs **no interpretation** of NIWIS data.

---

### catalog.py

Responsible for

- downloading the station catalogue
- parsing catalogue entries
- filtering measurement types
- nearest-station lookup

The catalogue layer has no knowledge of Home Assistant.

---

### mapper.py

Responsible for transforming NIWIS payloads into provider-independent models.

Currently this includes

- station mapping
- observation mapping
- trend calculation
- rolling statistics
- quality handling
- placeholder filtering

The mapper contains the majority of the provider intelligence.

---

### const.py

Contains NIWIS-specific constants.

Examples include

- measurement type mappings
- placeholder values
- endpoint constants

Provider constants are intentionally kept separate from
`custom_components/hydro_monitor/const.py`.

---

## Core models

The provider produces exactly two primary models.

### HydroStation

Represents relatively static information.

Examples

- station identifier
- coordinates
- catchment
- elevations
- operator
- institution
- historical metadata

Station metadata changes only rarely.

---

### HydroObservation

Represents dynamic measurements.

Examples

- current value
- observation date
- trends
- rolling statistics
- quality flag

Observations change continuously as new NIWIS measurements become available.

Keeping both models separate avoids unnecessary updates of static metadata.

---

## Coordinator

The coordinator forms the bridge between the provider layer and Home Assistant.

Responsibilities

- scheduled updates
- update status
- error propagation
- current observation
- associated station

The coordinator never performs NIWIS-specific parsing.

Instead it requests already mapped provider-independent models.

---

## Entity Layer

Hydro Monitor intentionally separates dynamic observations from static metadata.

Two entity classes currently exist.

### HydroObservationSensor

Represents

- current value
- trends
- rolling statistics
- observation quality
- observation age

---

### HydroStationSensor

Represents

- station metadata
- hydrological metadata
- administrative metadata
- historical metadata

Metadata entities are created only when a corresponding value exists.

This prevents large numbers of permanently unavailable entities.

---

## Why this architecture?

Several alternative approaches were considered during development.

For example

- exposing NIWIS payloads directly
- attaching all metadata as attributes
- creating one entity class for everything

All were rejected.

The chosen architecture offers

- excellent testability
- provider independence
- clean separation of concerns
- easy future extension
- small and understandable classes
- reusable provider logic

These advantages become increasingly important as support for Derived
Quantities, Climate Indicators and additional providers is added.

---

# 3. Station Catalogue and Metadata

## Overview

The NIWIS station catalogue forms the foundation of the Hydro Monitor
integration.

Unlike many environmental APIs, the station catalogue contains considerably more
than simple station coordinates and names. Depending on the measurement type,
NIWIS exposes extensive hydrological, geographical and administrative metadata.

Hydro Monitor maps this information into the provider-independent
`HydroStation` model.

The mapping is intentionally conservative.

Fields are only interpreted where their meaning has been verified through

- official documentation,
- inspection of multiple station payloads,
- consistent behaviour across the station catalogue.

Fields whose semantics remain uncertain are preserved unchanged rather than
being translated into potentially incorrect terminology.

---

# Station lifecycle

Every configured station follows the same lifecycle.

```text
NIWIS Station Catalogue
          │
          ▼
Raw JSON payload
          │
          ▼
Validation
          │
          ▼
Field Mapping
          │
          ▼
HydroStation
          │
          ▼
Config Entry Runtime Data
          │
          ▼
HydroStationSensor entities
```

Station metadata is loaded during configuration and reused during normal
operation.

Unlike observations, station metadata changes only rarely.

---

# Design Principles

Several principles govern the implementation of the station model.

## Provider independence

The `HydroStation` model contains no NIWIS-specific field names.

Examples

| NIWIS | Hydro Monitor |
|--------|---------------|
| gkz | waterbody_code |
| ezgGroesse | catchment_area_km2 |
| hoehePnp | gauge_zero_elevation |
| lageGewaesser | waterbody_position |

Future providers should populate the same model using their own field names.

---

## Optional metadata

Not every station provides every field.

For example

- groundwater stations often have hydrogeological regions,
- river gauges usually provide catchment areas,
- spring stations frequently provide locality information,
- historical low-water statistics are measurement-type dependent.

Consequently almost every metadata field is optional.

Missing information is represented by `None`.

The integration never invents missing metadata.

---

## Immutable station metadata

Hydro Monitor treats station metadata as effectively static.

Examples include

- station name,
- coordinates,
- catchment area,
- operator,
- gauge elevations,
- hydrogeological region.

These values are loaded once and reused throughout the lifetime of the config
entry.

Observation updates therefore never recreate station objects unless the
configuration itself changes.

This reduces unnecessary allocations and simplifies entity handling.

---

# Metadata Categories

For clarity, Hydro Monitor groups station metadata into logical categories.

## 3.1 Identification

The following fields uniquely identify a station.

| HydroStation | Description |
|--------------|-------------|
| provider | Data provider identifier |
| station_id | Provider-specific station identifier |
| name | Human-readable station name |
| measurement_types | Supported hydrological measurements |

The combination

```
provider + station_id
```

uniquely identifies the physical station within a provider.

Within Home Assistant, the configured measurement type is additionally included
in the device identifier to distinguish stations exposing multiple measurement
types.

---

## 3.2 Geographic Information

Geographic metadata describes the physical location of the monitoring station.

| Field | Description |
|-------|-------------|
| latitude | WGS84 latitude |
| longitude | WGS84 longitude |
| locality | Nearby town or locality |
| station_type | NIWIS station classification |

Coordinates are primarily used for

- nearby station discovery,
- distance calculation,
- future map visualisation.

No reverse geocoding is currently performed.

---

## 3.3 Hydrological Information

Hydrological metadata describes the monitored water body.

| Field | Description |
|-------|-------------|
| waterbody | Name of river or water body |
| waterbody_code | Official Gewässerkennzahl (GKZ) |
| waterbody_position | River kilometre |
| catchment_area_km2 | Catchment size |

This information is available primarily for river stations.

Groundwater stations typically provide alternative hydrogeological metadata
instead.

---

## River kilometre

The NIWIS field

```
lageGewaesser
```

is exposed in Hydro Monitor as

```
waterbody_position
```

and displayed as

```
River kilometre
```

with the native unit

```
km
```

Internally the value is stored independently of any provider-specific wording.

---

## 3.4 Elevation Information

Several elevation systems exist within NIWIS.

Hydro Monitor distinguishes between

| Field | Meaning |
|-------|---------|
| elevation_ground | Ground elevation |
| gauge_zero_elevation | Gauge zero elevation |
| elevation_system | Height reference system |

Gauge zero elevation is especially important for interpreting water level
measurements.

Ground elevation is particularly relevant for groundwater monitoring.

---

## Height reference systems

Observed reference systems include

```
DHHN12
```

Future NIWIS changes may introduce additional reference systems.

Hydro Monitor intentionally preserves the original provider value.

No normalisation is currently performed.

---

## 3.5 Hydrogeological Information

Groundwater monitoring exposes additional metadata describing the geological
context.

Observed fields include

- hydrogeological region
- hydrogeological region code

Typical examples include

- Süddeutsches Moränenland
- Süddeutsches Tertiärhügelland

These fields are not generally applicable to river gauges.

---

## 3.6 Administrative Information

Administrative metadata identifies the organisation responsible for the station.

Examples include

- operator
- institution
- operator URL
- institution URL
- source URL
- licence

Hydro Monitor intentionally preserves the original values.

Only licence strings are lightly normalised for presentation where the mapping
is unambiguous.

---

## 3.7 Historical Metadata

One of the more interesting discoveries during development was that NIWIS also
provides historical reference values directly within the station catalogue.

These include

- historical NQ
- historical NQ date
- historical NW
- historical NW date

Unlike rolling statistics, these values represent official historical reference
information and therefore belong to the station rather than the observation
model.

Hydro Monitor exposes them as dedicated station sensors.

The entities are only created when they are hydrologically applicable.

For example

- NQ is available for discharge stations,
- NW is available for water level stations.

Groundwater stations currently do not expose corresponding entities because no
verified equivalent has been identified.

---

# Why separate metadata sensors?

Earlier prototypes attached every station field as an attribute of the primary
observation sensor.

This approach was abandoned.

Reasons include

- very large attribute sets,
- duplicated metadata,
- poor discoverability,
- difficult localisation,
- inability to individually enable or disable fields.

Dedicated metadata entities provide a much cleaner Home Assistant experience.

The resulting device page behaves similarly to high-quality built-in Home
Assistant integrations where static device information is exposed through
separate entities rather than oversized attribute dictionaries.

---

# 4. Observation Data and Processing

## Overview

Station metadata describes the monitoring location. Observations describe its
changing hydrological state.

Hydro Monitor maps NIWIS time-series records into the provider-independent
`HydroObservation` model.

The observation-processing pipeline is deliberately defensive because NIWIS
series may contain:

- missing dates,
- irregular update intervals,
- technical placeholder values,
- non-numeric values,
- quality flags,
- gaps between observations,
- unsorted records,
- incomplete periods.

The mapper validates and normalises the raw records before selecting a current
value or calculating statistics.

```text
NIWIS time-series response
          │
          ▼
Raw observation records
          │
          ▼
Date and numeric parsing
          │
          ▼
Placeholder filtering
          │
          ▼
Valid observations
          │
          ▼
Chronological ordering
          │
          ├── Current observation
          ├── 1-day change
          ├── 7-day change
          ├── 30-day minimum
          ├── 30-day maximum
          └── Sample count
          │
          ▼
HydroObservation
```

---

## 4.1 The `HydroObservation` model

`HydroObservation` represents the latest valid measurement together with locally
calculated supporting information.

The current model contains:

| Field | Description |
|---|---|
| `measurement_type` | Provider-independent measurement type |
| `value` | Latest valid measured value |
| `unit` | Native unit returned for the measurement |
| `observed_on` | Date of the latest valid observation |
| `quality_flag` | Quality flag belonging to the latest observation |
| `change_1d` | Change compared with approximately one day earlier |
| `change_7d` | Change compared with approximately seven days earlier |
| `minimum_30d` | Minimum valid value in the recent period |
| `maximum_30d` | Maximum valid value in the recent period |
| `sample_count` | Number of valid observations used |

The model intentionally contains no NIWIS field names or raw response objects.

All provider-specific interpretation must happen before the model reaches the
coordinator or entity layer.

---

## 4.2 Raw observation records

A NIWIS time-series record generally contains:

- a date or timestamp,
- a measured value,
- optionally a quality flag.

The exact payload structure can differ between endpoints and measurement types.

A record is considered usable only when:

1. its date can be parsed;
2. its value can be converted to a numeric value;
3. the value is not a known NIWIS technical placeholder.

Invalid records are ignored individually.

One malformed record must not cause the complete station update to fail when
other valid observations remain available.

---

## 4.3 Date handling

Observation dates are parsed defensively.

The integration accepts ISO-like date values and uses the date component of the
source value.

Examples of values that may be reduced to a date include:

```text
2026-07-15
2026-07-15T00:00:00
2026-07-15T00:00:00+02:00
```

The current provider model stores `observed_on` as a `date`.

This reflects the NIWIS series examined during development, which were primarily
used as dated hydrological observations rather than exact sub-daily event
timestamps.

Invalid dates are ignored.

Hydro Monitor does not:

- replace an invalid date with the current date;
- infer a missing date from neighbouring records;
- generate synthetic timestamps.

If future NIWIS endpoints provide meaningful sub-daily values, the model may
need to distinguish between:

- observation date,
- exact observation timestamp,
- API retrieval timestamp.

---

## 4.4 Numeric parsing

Observation values are converted defensively to floating-point numbers.

Accepted examples include:

```text
13
13.0
"13.0"
```

Rejected examples include:

```text
null
""
"not-a-number"
```

A failed conversion affects only the corresponding observation record.

Other valid records in the same response remain usable.

---

## 4.5 Technical placeholder values

NIWIS uses negative technical values that must not be interpreted as real
hydrological measurements.

Hydro Monitor currently filters:

| Value | Current treatment |
|---:|---|
| `-777` | Technical placeholder |
| `-888` | Technical placeholder |
| `-999` | Technical placeholder |
| `-9999` | Technical placeholder |

These values are removed before any further processing.

They must never affect:

- the current sensor value;
- trend calculations;
- minimum or maximum calculations;
- sample counts;
- trend classification.

The exact official distinction between these values has not yet been verified.

Hydro Monitor therefore documents them conservatively as technical placeholders
instead of assigning unsupported meanings such as “missing”, “invalid” or
“temporarily unavailable”.

### Why placeholder filtering happens first

Filtering placeholders at the beginning of the pipeline ensures that every
later calculation operates on the same validated observation set.

Without central filtering, a value such as `-777` could incorrectly become:

- the latest measurement;
- the thirty-day minimum;
- a very large negative trend;
- a misleading Home Assistant history value.

Placeholder filtering is therefore a mandatory prerequisite for every
observation calculation.

---

## 4.6 Chronological ordering

NIWIS responses are not assumed to arrive in chronological order.

After parsing and filtering, all valid observations are ordered by date.

Example raw order:

```text
2026-07-08   10.0
2026-07-15   13.0
2026-06-20    8.0
2026-07-14   12.0
```

Chronological interpretation:

```text
2026-06-20    8.0
2026-07-08   10.0
2026-07-14   12.0
2026-07-15   13.0
```

The latest valid observation is therefore:

```text
2026-07-15   13.0
```

The mapper must never assume that the first or last raw array element is the
current value.

---

## 4.7 Duplicate dates

The sampled NIWIS data did not establish a complete authoritative rule for
duplicate observation dates.

Possible causes could include:

- corrected measurements;
- multiple publication stages;
- records with different quality flags;
- sub-daily observations reduced to the same date.

Before duplicate-date behaviour becomes part of the public integration contract,
the current mapper behaviour should be reviewed explicitly.

Possible future selection criteria include:

1. exact timestamp;
2. publication order;
3. quality flag;
4. corrected-value status.

Until verified, duplicate-date handling remains an open implementation detail.

---

## 4.8 Selecting the current observation

The current observation is the valid record with the latest parsed date.

Its fields populate:

- `value`;
- `observed_on`;
- `quality_flag`;
- `unit`.

The current observation does not depend on:

- the raw API array order;
- whether an exact observation exists for every previous day;
- whether the time series contains invalid records.

If no valid observation remains after filtering, the mapper returns an empty or
unavailable observation state according to the current model.

---

## 4.9 Quality flags

The quality flag associated with the latest valid observation is preserved in
`HydroObservation.quality_flag`.

Observed values include:

```text
A
BfGAdded
```

The integration currently does not:

- reject an observation because its flag is unfamiliar;
- rank flags by quality;
- calculate a confidence percentage;
- translate the provider value into a guessed description.

Unknown flags are preserved unchanged.

This conservative handling prevents information loss and allows future support
without changing historical observations.

The exact official semantics of all NIWIS quality flags remain an open
documentation task.

---

## 4.10 One-day change

The one-day change compares the latest valid observation with a suitable earlier
valid observation near:

```text
latest observation date - 1 day
```

NIWIS series may contain gaps. An exact observation on the target date is
therefore not required.

When the exact date is unavailable, Hydro Monitor uses the nearest suitable
previous valid observation according to the mapper logic.

Example:

```text
Latest observation:        2026-07-15   13.0
Target comparison date:    2026-07-14
Available previous value:  2026-07-13   12.0
Calculated change:                         1.0
```

The calculation is:

```text
latest valid value - comparison value
```

A positive result indicates an increase.

A negative result indicates a decrease.

---

## 4.11 Seven-day change

The seven-day change uses the same principle with a target date approximately
seven days before the latest observation.

```text
latest observation date - 7 days
```

An exact-date record is not required.

This is important for:

- delayed publication;
- weekends;
- sparse spring-discharge series;
- incomplete groundwater records;
- individual invalid or placeholder observations.

The calculation remains based solely on actual valid records.

---

## 4.12 No interpolation

Hydro Monitor does not interpolate missing observations.

Example:

```text
2026-07-13   12.0
2026-07-15   13.0
```

The integration does not create a synthetic value for `2026-07-14`.

Reasons:

- interpolation would create a value that NIWIS never measured;
- hydrological values can change abruptly;
- sparse measurement types may not justify linear assumptions;
- different providers may use different publication intervals;
- transparency is preferred over apparent completeness.

Only real valid observations are used.

---

## 4.13 Thirty-day statistics

Hydro Monitor calculates recent rolling statistics from the validated series.

Currently exposed values include:

- thirty-day minimum;
- thirty-day maximum;
- valid sample count.

### Minimum

The minimum is the lowest valid observed value within the relevant recent
period.

Technical placeholders and invalid records are excluded.

### Maximum

The maximum is the highest valid observed value within the relevant recent
period.

### Sample count

`sample_count` indicates how many valid observations were available for the
calculation.

This provides useful context.

A range calculated from thirty valid observations has a different evidential
basis from a range calculated from only three observations.

Hydro Monitor currently exposes the count but does not yet calculate a formal
data-completeness percentage.

---

## 4.14 Empty or invalid series

The mapper supports time series containing no usable observations.

Examples include:

- an empty API response;
- a series containing only placeholder values;
- a series containing only invalid dates;
- a series containing only non-numeric values.

The integration must not crash the complete config entry in these cases.

Instead, the corresponding entities become unavailable or expose an empty state
according to the current coordinator and entity behaviour.

This allows:

- later automatic recovery;
- diagnostics access;
- system-health reporting;
- continued operation of other configured stations.

---

## 4.15 Measurement units

NIWIS exposes measurement-specific native units.

Observed examples include:

| Measurement type | Example unit |
|---|---|
| Discharge | `m³/s` |
| Water level | `cm` |
| Groundwater level | `m. ü. NHN` |
| Spring discharge | `l/s` |

The primary observation entity preserves the native unit.

### Difference and trend units

Trend entities represent a change rather than an absolute state.

For display consistency, changes may be converted to a more suitable unit.

Examples observed in Home Assistant include:

- water-level changes displayed in millimetres;
- groundwater-level changes displayed in millimetres;
- current groundwater values retained in metres above the height reference;
- discharge and spring-discharge changes retaining volumetric-flow semantics.

Unit conversion must remain measurement-aware.

A numeric difference must never receive a unit that changes its physical
meaning.

---

## 4.16 Last observation date

The latest observation date is exposed separately from the primary numeric
measurement.

This allows users to answer:

```text
On which date was this value observed?
```

The value is represented as a date entity where appropriate.

It must not be confused with:

- the Home Assistant entity update time;
- the API retrieval time;
- the coordinator refresh time.

---

## 4.17 Measurement age

Hydro Monitor also exposes the age of the latest observation.

This answers a different question:

```text
How old is the currently displayed measurement?
```

Measurement age is useful for:

- stale-data detection;
- dashboards;
- notifications;
- automations;
- diagnostics.

A measurement can remain numerically valid while being older than expected.

---

## 4.18 Availability and stale data

Two concepts must remain separate.

### Coordinator availability

Describes whether the latest provider update succeeded.

### Measurement freshness

Describes how old the latest valid station observation is.

The API can be reachable while a particular station has not published a recent
measurement.

Conversely, a temporary API failure can occur while the last stored observation
is still recent and useful.

Hydro Monitor should therefore avoid treating API availability and data
freshness as the same condition.

---

## 4.19 Local trend classification

Hydro Monitor converts recent numeric changes into a qualitative local trend
state.

Current states include:

```text
strongly rising
rising
stable
falling
strongly falling
```

This classification is calculated locally.

It is not an official NIWIS low-water class.

The distinction is fundamental:

| Local Hydro Monitor trend | Official NIWIS classification |
|---|---|
| Based on recent raw-value change | Based on NIWIS calculation logic |
| Provider-independent | Provider-specific |
| Indicates direction | May indicate hydrological severity or category |
| Already implemented | Planned through derived quantities |

Future code, translations and documentation must keep these concepts clearly
separated.

---

## 4.20 Observation entities

The current observation model supports Home Assistant entities including:

- current measurement;
- one-day trend;
- seven-day trend;
- thirty-day minimum;
- thirty-day maximum;
- local trend status;
- last observation date;
- measurement age.

All entities read from the same coordinator data.

They do not trigger separate NIWIS requests.

This guarantees that values shown during one update cycle are internally
consistent.

---

## 4.21 Primary entity attributes

The primary observation entity intentionally exposes only a small set of
attributes.

These include:

- provider;
- station ID;
- observation date;
- quality flag;
- sample count.

Station metadata was deliberately removed from the primary observation entity
and exposed through dedicated station metadata entities.

This prevents duplicated information and keeps the primary entity focused on the
measurement.

---

## 4.22 Coordinator update lifecycle

The observation update process is:

```text
Scheduled coordinator refresh
          │
          ▼
NIWIS time-series request
          │
          ▼
Raw payload retrieval
          │
          ▼
Validation and mapping
          │
          ▼
New HydroObservation
          │
          ▼
Coordinator data replacement
          │
          ▼
All observation entities update
```

Locally calculated entities do not make their own API calls.

This reduces:

- network traffic;
- API load;
- update timing differences;
- inconsistent sensor states.

---

## 4.23 Trust and transparency principles

Observation processing follows these rules:

1. Never expose a technical placeholder as a real measurement.
2. Never invent a missing date.
3. Never interpolate a missing value without an explicit future design decision.
4. Preserve unknown quality flags.
5. Calculate statistics only from valid records.
6. Expose sample count where it provides useful context.
7. Distinguish provider availability from measurement freshness.
8. Distinguish local trends from official NIWIS classifications.
9. Prefer unavailable data over misleading data.
10. Keep NIWIS-specific assumptions inside the provider layer.

These principles should also guide:

- official derived-quantity support;
- climate indicators;
- historical statistics;
- future hydrological providers.

---

# 5. Data Quality and Measurement-Type Characteristics

## Overview

One of the primary objectives during the development of Hydro Monitor was not
only to integrate the NIWIS API, but also to understand the quality and
behaviour of the underlying data.

For this purpose, the project includes dedicated discovery tooling that
systematically analysed

- station catalogues,
- observation series,
- metadata completeness,
- quality flags,
- placeholder values,
- derived endpoints.

The findings documented in this chapter are based on sampled NIWIS stations and
the generated inventory contained in the project repository.

They should therefore be interpreted as observed characteristics rather than
official guarantees of the NIWIS API.

---

## 5.1 Why data quality matters

Hydrological measurements differ significantly from many sensor integrations.

A Home Assistant integration can usually assume that

- every sensor reports regularly,
- measurements are valid,
- missing values are rare.

The NIWIS API cannot make these assumptions.

Depending on the measurement type, observation series may contain

- technical placeholder values,
- quality annotations,
- irregular update intervals,
- missing observations,
- measurement-type-specific metadata,
- varying historical coverage.

Understanding these differences was therefore considered an essential part of
the implementation rather than an optional optimisation.

---

## 5.2 Discovery methodology

The project contains a dedicated discovery tool that sampled representative
stations across all currently supported measurement types.

The discovery process analysed

- station metadata,
- observation availability,
- placeholder occurrence,
- quality flags,
- endpoint schemas,
- derived quantities.

The resulting inventory was exported into the `niwis_inventory` directory and
serves as the factual basis for many implementation decisions.

---

## 5.3 Sampled measurement types

The current discovery covers four measurement categories.

| Measurement type | Typical example |
|------------------|-----------------|
| Discharge | River gauges |
| Water level | River level gauges |
| Groundwater level | Observation wells |
| Spring discharge | Springs |

Each measurement type exhibits noticeably different characteristics.

---

## 5.4 Observation completeness

The sampled stations produced the following results.

| Measurement type | Valid observations | Invalid observations |
|------------------|------------------:|---------------------:|
| Discharge | 300 | 0 |
| Water level | 300 | 0 |
| Groundwater level | 297 | 3 |
| Spring discharge | 162 | 138 |

These numbers describe the sampled stations only.

They are nevertheless useful because they demonstrate that measurement quality
varies significantly between station types.

---

## 5.5 Discharge observations

Discharge stations produced the highest quality dataset.

Observed characteristics include

- complete observation series,
- no placeholder values,
- consistent metadata,
- stable update behaviour.

As a result, discharge stations currently require the least defensive handling.

---

## 5.6 Water level observations

Water-level stations behaved similarly to discharge stations.

Observed characteristics include

- complete sampled series,
- no technical placeholders,
- good metadata completeness,
- stable observation history.

Water-level stations additionally provide several river-specific metadata fields
that are not available for groundwater stations.

Examples include

- river kilometre,
- catchment area,
- gauge zero elevation.

---

## 5.7 Groundwater observations

Groundwater stations were generally of high quality but differed in several
important aspects.

Observed characteristics include

- occasional missing observations,
- quality flags,
- hydrogeological metadata,
- ground elevation instead of gauge zero elevation.

Groundwater stations also provide metadata that is unique to groundwater
monitoring.

Examples include

- hydrogeological region,
- hydrogeological region code,
- locality.

These fields are therefore represented as optional metadata within
`HydroStation`.

---

## 5.8 Spring-discharge observations

Spring-discharge stations showed the greatest variability.

Observed characteristics include

- frequent placeholder values,
- lower observation completeness,
- quality annotations,
- larger gaps in the sampled series.

The discovery process identified a large number of `-777` placeholder values.

Consequently, placeholder filtering became a fundamental requirement of the
observation-processing pipeline rather than a measurement-type-specific special
case.

---

## 5.9 Placeholder values

The sampled datasets contained several technical placeholder values.

Currently recognised values include

```text
-777
-888
-999
-9999
```

These values are treated as invalid observations.

At present, the project deliberately avoids assigning undocumented semantic
meanings to individual placeholder codes.

Instead they are collectively handled as technical placeholders until official
documentation becomes available.

---

## 5.10 Quality flags

Quality annotations were observed in several measurement types.

Known values currently include

```text
A
BfGAdded
```

The exact official semantics of these values have not yet been verified.

Hydro Monitor therefore follows a conservative strategy.

Quality flags are

- preserved,
- exposed,
- documented,

but not interpreted beyond their observed existence.

---

## 5.11 Metadata completeness

Metadata availability differs considerably between measurement types.

Examples include

| Metadata | River stations | Groundwater | Springs |
|-----------|---------------|------------|----------|
| Catchment area | ✔ | — | partial |
| River kilometre | ✔ | — | partial |
| Gauge zero elevation | ✔ | — | — |
| Ground elevation | — | ✔ | ✔ |
| Hydrogeological region | — | ✔ | ✔ |
| Locality | partial | ✔ | ✔ |

This variability is the primary reason why Hydro Monitor stores nearly all
station metadata as optional fields.

---

## 5.12 Lessons learned

Several implementation decisions originated directly from the discovery
exercise.

Examples include

- placeholder filtering before any calculations,
- provider-independent station models,
- optional metadata fields,
- dedicated metadata entities,
- defensive observation parsing,
- preserving unknown quality flags,
- separating observations from station information.

Without the discovery process, several of these design decisions would likely
have been different.

---

## 5.13 Implications for future development

The observed differences between measurement types should also guide future
development.

In particular,

- derived quantities should not automatically be assumed to exist for every
  measurement type;
- metadata entities should continue to be created dynamically;
- future providers should follow the same defensive mapping principles;
- climate indicators should account for varying observation completeness.

The discovery phase demonstrated that hydrological APIs should not be treated
like conventional IoT sensor APIs.

Instead, Hydro Monitor should continue to prioritise

- correctness,
- transparency,
- provider independence,
- graceful handling of incomplete data.

These principles have proven robust across all sampled NIWIS measurement types.

---

# 6. Reverse Engineering the NIWIS API

## Overview

The public NIWIS API documentation provides a solid introduction to the
available endpoints but intentionally focuses on the officially supported
interface.

During the development of Hydro Monitor it became apparent that a significantly
larger amount of information could be obtained through systematic exploration of
the API.

Rather than implementing only the documented endpoints, Hydro Monitor includes a
set of discovery tools that analyse the complete public API.

The objectives were:

- identify undocumented fields;
- understand endpoint relationships;
- evaluate metadata completeness;
- analyse observation quality;
- discover derived quantities;
- compare measurement types;
- detect inconsistencies;
- build a reproducible knowledge base.

This chapter documents that process.

---

# 6.1 Motivation

Early versions of Hydro Monitor relied almost exclusively on the official API
documentation.

While this was sufficient for retrieving observations, several important
questions remained unanswered.

Examples included:

- Which metadata fields always exist?
- Which fields are measurement-type specific?
- Which values are placeholders?
- Which quality flags exist?
- Which derived quantities are available?
- Which endpoints require additional parameters?
- Which values are optional?
- Which values can safely be interpreted?

Answering these questions required analysing the API itself rather than relying
solely on the published documentation.

---

# 6.2 Discovery philosophy

The discovery tooling follows one fundamental principle:

> Observe first. Interpret later.

Whenever possible, Hydro Monitor prefers documenting observed API behaviour over
making assumptions.

For example:

✔ observed:

- field exists
- field is always numeric
- field appears only for groundwater stations
- placeholder value occurs

✘ avoided:

- undocumented meaning
- inferred semantics
- guessed engineering units
- speculative classifications

This conservative philosophy greatly reduces the risk of introducing incorrect
behaviour into the provider.

---

# 6.3 Discovery workflow

The complete discovery process consists of several independent stages.

```text
Download station catalogue
            │
            ▼
Collect station metadata
            │
            ▼
Select representative stations
            │
            ▼
Download observations
            │
            ▼
Analyse metadata completeness
            │
            ▼
Analyse quality flags
            │
            ▼
Analyse placeholder values
            │
            ▼
Discover derived endpoints
            │
            ▼
Generate inventory
```

Every stage produces artefacts that can be inspected independently.

---

# 6.4 Inventory generation

The discovery tooling generates a local inventory describing the analysed API.

The inventory includes information such as

- discovered stations,
- metadata fields,
- measurement types,
- endpoint availability,
- derived quantities,
- quality flags,
- placeholder values,
- observation statistics.

The inventory is intentionally stored separately from the provider itself.

It serves as

- development documentation,
- regression reference,
- reverse engineering archive.

Rather than repeatedly querying the public API during development, many analyses
can be performed directly against the generated inventory.

---

# 6.5 Why an inventory?

The inventory fulfils several important purposes.

## Reproducibility

Discovery results become reproducible.

Future contributors can compare inventories generated at different points in
time.

---

## Regression detection

If NIWIS changes

- field names,
- endpoint schemas,
- metadata,
- quality flags,

the differences become immediately visible.

---

## Offline analysis

Many implementation decisions can be revisited without repeatedly accessing the
live API.

---

## Documentation

The inventory serves as supporting evidence for this technical reference.

Whenever possible, implementation decisions should be based on observed
inventory data rather than anecdotal testing.

---

# 6.6 Discovery tools

Hydro Monitor currently includes several discovery utilities.

Examples include:

- station catalogue explorer;
- metadata inventory generator;
- nearby station discovery;
- derived endpoint discovery;
- observation sampler.

Each tool has a single responsibility.

This modular design makes it easier to repeat individual analyses as the NIWIS
API evolves.

---

# 6.7 Reverse engineered metadata

The discovery process identified considerably more metadata than initially
expected.

Examples include:

- catchment size;
- hydrogeological region;
- river kilometre;
- gauge elevations;
- historical NQ values;
- historical NW values;
- licence information;
- institution metadata;
- URLs;
- locality information.

Many of these fields are either only briefly documented or not explicitly
highlighted in the public documentation.

Hydro Monitor exposes them whenever their meaning has been verified.

---

# 6.8 Reverse engineered quality behaviour

Systematic observation sampling revealed several recurring patterns.

Examples include:

- placeholder values;
- quality flags;
- varying observation completeness;
- measurement-type-specific metadata;
- irregular update frequencies.

These findings directly influenced the implementation of

- defensive parsing;
- placeholder filtering;
- optional metadata;
- dedicated station entities.

---

# 6.9 Reverse engineered endpoint families

Perhaps the most significant discovery concerned the structure of the NIWIS API
itself.

Beyond the documented observation endpoints, the API exposes multiple endpoint
families providing derived hydrological information.

Examples include:

- characteristic values;
- percentile statistics;
- historical low-water indicators;
- exceedance frequencies;
- climate indicators;
- additional statistical summaries.

Many of these endpoints are independent from the primary observation endpoint.

This explains why Hydro Monitor treats derived quantities as a dedicated
implementation phase rather than additional observation attributes.

---

# 6.10 Lessons learned

Several architectural decisions originated directly from the discovery process.

Examples include:

- separating observations from metadata;
- provider-independent models;
- dynamic metadata entities;
- defensive mapping;
- preserving unknown values;
- documenting uncertainty explicitly.

Without systematic reverse engineering, many of these decisions would likely
have relied on assumptions rather than evidence.

---

# 6.11 Future discovery

Discovery should not be considered a one-time activity.

Whenever NIWIS introduces

- new endpoints;
- new metadata fields;
- new measurement types;
- additional providers;
- revised schemas,

the discovery tooling should be rerun.

The resulting inventory should then be compared with previous versions before
implementation changes are made.

Maintaining this workflow helps ensure that Hydro Monitor evolves in step with
the underlying data source while preserving backward compatibility whenever
possible.

---

# 7. Official NIWIS Derived Quantities

## Overview

The NIWIS API provides more than raw observations and station metadata.

It also exposes official server-side calculations that interpret observations
within a hydrological, historical or climatological context.

Hydro Monitor refers to these calculations as **derived quantities**.

Examples include:

- characteristic discharge values;
- low-water classifications;
- percentile and decile statistics;
- historical reference values;
- classification boundaries;
- climate indicators;
- low-flow indices;
- development indicators.

These values are fundamentally different from the locally calculated
one-day and seven-day changes already exposed by Hydro Monitor.

```text
Raw NIWIS observations
          │
          ├── Local Hydro Monitor calculations
          │      ├── 1-day change
          │      ├── 7-day change
          │      ├── 30-day minimum
          │      ├── 30-day maximum
          │      └── local trend state
          │
          └── Official NIWIS derived quantities
                 ├── hydrological statistics
                 ├── classifications
                 ├── category results
                 ├── reference values
                 └── climate indicators
```

The two branches must remain separate in code, naming and documentation.

---

## 7.1 Discovery status

The discovery tooling identified a catalogue of official NIWIS calculations.

At the time of the analysed inventory:

- 43 derived quantities were discovered;
- 8 endpoint families were identified;
- all 43 discovered calculations could be probed successfully using the tested
  request patterns.

This is a significant result, but it must be interpreted carefully.

A successful probe demonstrates that an endpoint can be called with the tested
parameters.

It does **not** yet prove that:

- the quantity is valid for every station;
- the quantity applies to every measurement type;
- the returned unit is always identical;
- every result is suitable as a default Home Assistant entity;
- the same reference period is appropriate for all users;
- the response semantics are completely understood.

The generated inventory remains the source of truth for the exact discovered
catalogue:

```text
niwis_inventory/derived_quantities.json
niwis_inventory/derived_probe_results.json
```

---

## 7.2 Why NIWIS calculates these values server-side

Many derived hydrological values require more information than the recent raw
time series currently requested by Hydro Monitor.

Possible inputs include:

- long historical observation periods;
- station-specific reference series;
- official classification thresholds;
- hydrological reference periods;
- provider-maintained correction rules;
- calendar-based aggregation;
- exceedance or non-exceedance frequencies.

Reimplementing such calculations locally would create several risks:

- divergence from official NIWIS results;
- incomplete historical data;
- undocumented assumptions;
- inconsistent classifications;
- difficult validation;
- increased maintenance effort.

Hydro Monitor should therefore prefer official NIWIS derived results whenever
an official endpoint exists and its semantics are understood.

Local calculations remain appropriate only where they are intentionally simple,
provider-independent and transparent, such as recent numeric change.

---

## 7.3 Endpoint families

The discovery process identified eight endpoint families.

```text
berechneEinzelwertNummer
berechneEinzelwertKategorie
berechneZeitreihenErgebnisNummer
berechneKlassifikationsgrenzeDynamisch
berechneKlassifikationsgrenzeStatisch
berechneKlimaindikatorNiedrigwassertage
berechneKlimaindikatorMonatlicheAbweichungenMittelwert
berechneLfi
```

The endpoint names indicate that NIWIS distinguishes between several result
shapes and calculation purposes.

### Numeric single-value endpoints

```text
berechneEinzelwertNummer
```

These endpoints return a numeric result for a selected derived quantity.

Typical candidates include:

- characteristic values;
- statistical reference values;
- numeric hydrological indicators.

The exact unit and interpretation depend on the selected quantity.

### Category endpoints

```text
berechneEinzelwertKategorie
```

These endpoints return a categorical result rather than a continuous numeric
value.

Potential examples include:

- low-water class;
- categorical hydrological status;
- classification labels.

Category values must be preserved accurately.

Translations should improve presentation without changing the official meaning.

### Time-series result endpoints

```text
berechneZeitreihenErgebnisNummer
```

These endpoints return a sequence of derived numeric values over time.

They may be suitable for:

- historical charts;
- monthly or annual development;
- derived-series statistics;
- trend analysis over official results.

They should not automatically be reduced to a single current value without an
explicit selection rule.

### Dynamic classification boundaries

```text
berechneKlassifikationsgrenzeDynamisch
```

Dynamic boundaries can vary over time or with the selected reference context.

Possible influences include:

- season;
- calendar date;
- reference period;
- recent hydrological behaviour;
- station-specific historical distribution.

Dynamic boundaries must therefore be refreshed rather than treated as static
station metadata.

### Static classification boundaries

```text
berechneKlassifikationsgrenzeStatisch
```

Static boundaries represent fixed classification limits for the relevant
station and calculation context.

They may still depend on:

- station;
- measurement type;
- selected classification method;
- reference period.

“Static” should therefore be understood as static within the selected method,
not necessarily universal across all stations.

### Low-water-day climate indicator

```text
berechneKlimaindikatorNiedrigwassertage
```

This endpoint family provides a climate-oriented count or series related to
low-water days.

Its interpretation depends on the threshold definition and reference period.

### Monthly mean-deviation climate indicator

```text
berechneKlimaindikatorMonatlicheAbweichungenMittelwert
```

This endpoint family provides monthly deviations from a reference mean.

Before implementation, Hydro Monitor must verify:

- whether the result is absolute or relative;
- the native unit;
- the reference period;
- whether positive and negative values have measurement-specific meanings.

### Low Flow Index

```text
berechneLfi
```

This endpoint calculates the LFI or Low Flow Index.

LFI is an expert hydrological indicator and should not be exposed without clear
user-facing documentation.

It is likely to be optional and disabled by default in the entity registry.

**Status: blocked, deferred past Sprint 5 (live-verified 2026-08-07).** All
5 discharge stations used for manual verification returned the official
NIWIS error `"Für diese Messstelle kann der LFI nicht berechnet werden."`
(`fehlermeldung`) — leaving no working sample to validate a mapper
against. The response envelope is also structurally more complex than
every other derived-quantity endpoint implemented so far (a nested
`duerreperiodenindizeProTag` per-day array plus a
`klassifikationProDuerreperiode` dict keyed by drought period, neither
confirmed successful). Implementing this blind is not justified given
ADR-004/ADR-006. Re-attempt only after a station returns a non-error
result, or NIWIS publishes the response schema.

---

## 7.4 Representative discovered quantities

The discovered catalogue includes different groups of values depending on the
measurement type.

The following examples are representative and are not a complete substitute for
`derived_quantities.json`.

### Discharge

Representative discovered discharge quantities include:

- MQ;
- MNQ;
- NQ;
- NM7Q;
- NM30Q;
- LFI;
- deciles;
- low-water class;
- development during the last seven days.

These values provide different kinds of information.

| Quantity | General role |
|---|---|
| MQ | Mean discharge reference |
| MNQ | Mean low-discharge reference |
| NQ | Low-discharge extreme or reference value |
| NM7Q | Low-flow statistic based on seven-day values |
| NM30Q | Low-flow statistic based on thirty-day values |
| LFI | Expert low-flow indicator |
| Deciles | Position within a historical distribution |
| Low-water class | Categorical hydrological classification |
| Seven-day development | Official recent-development indicator |

The exact official calculation definition, period and return unit must be taken
from NIWIS metadata or verified endpoint behaviour before implementation.

### Water level

Representative discovered water-level quantities include:

- MW;
- MNW;
- median;
- low-water class;
- days below defined limits.

Water-level statistics must not be mixed with discharge statistics even where
abbreviations look similar.

### Groundwater level

Representative groundwater quantities include:

- metres below ground level;
- low-water class;
- classifications;
- static and dynamic classification limits.

This is particularly useful because the primary groundwater value may be
reported as an absolute elevation, while a derived result can express the level
relative to ground surface or historical context.

### Spring discharge

Spring-discharge support must be evaluated cautiously.

The sampled raw series showed lower completeness and many placeholders.

A derived endpoint may still return an official result, but Hydro Monitor should
verify applicability and update behaviour per quantity before creating entities.

---

## 7.5 Result types

Derived quantities should not be forced into one universal model.

At minimum, the implementation must support several result types.

### Numeric result

Example conceptual structure:

```text
value: 14.2
unit: m³/s
```

### Category result

Example conceptual structure:

```text
code: 2
label: low
```

The actual NIWIS response structure must be mapped without inventing category
codes or labels.

### Boundary result

Example conceptual structure:

```text
lower: 10.0
upper: 15.0
unit: m³/s
```

Some classifications may contain several ordered boundaries rather than one
lower and upper pair.

### Time-series result

Example conceptual structure:

```text
2026-01-01  value
2026-02-01  value
2026-03-01  value
```

### Indicator result

Expert or climate indicators may include additional metadata such as:

- reference period;
- threshold;
- calculation method;
- category;
- unit;
- time interval.

The provider-independent result model must preserve this context.

---

## 7.6 Parameter dimensions

Derived calculations can require different combinations of parameters.

Observed or inferred parameter dimensions include:

- station identifier;
- measurement type;
- derived-quantity identifier;
- start date;
- end date;
- reference-period start;
- reference-period end;
- classification method;
- interval or aggregation period.

The implementation must not assume that one request builder can call all eight
endpoint families with the same argument set.

A registry-based design is preferable.

Conceptual example:

```python
DerivedQuantityDefinition(
    key="low_water_class",
    endpoint_family="single_category",
    supported_measurement_types={...},
    requires_station=True,
    requires_reference_period=False,
    result_type="category",
)
```

This is an architectural direction, not yet a committed public API.

---

## 7.7 Provider-independent derived result model

Derived results should be mapped into provider-independent models before they
reach Home Assistant.

A future model may need fields such as:

```text
provider
station_id
measurement_type
quantity_key
value
category
unit
observed_on
period_start
period_end
reference_period_start
reference_period_end
boundaries
metadata
```

Not every field applies to every result.

The model should therefore be designed around optional typed fields or separate
result variants.

A single unstructured dictionary would be easy initially but would weaken:

- type checking;
- tests;
- translation handling;
- future provider support;
- entity consistency.

---

## 7.8 Update strategy

Derived quantities do not necessarily require the same refresh interval as raw
observations.

Examples:

- current low-water class may change when the latest observation changes;
- static boundaries may change only when provider reference data changes;
- climate indicators may change monthly or annually;
- historical statistics may change rarely;
- dynamic boundaries may require daily refreshes.

Using one interval for every derived value would create unnecessary API calls.

A future update strategy should classify quantities as:

| Update class | Example behaviour |
|---|---|
| Observation-coupled | Refresh with every raw observation update |
| Daily | Refresh once per day |
| Monthly | Refresh after a new monthly period |
| Static or rare | Cache for a long period |
| Manual or on-demand | Calculate only when enabled or requested |

Caching must remain transparent and must not hide failed refreshes.

---

## 7.9 Home Assistant entity strategy

Hydro Monitor should not create 43 new entities for every station by default.

That would produce:

- crowded device pages;
- unnecessary API calls;
- many irrelevant entities;
- difficult onboarding;
- higher maintenance cost.

Instead, quantities should be grouped by user value and complexity.

### Recommended default entities

Likely candidates for enabled-by-default entities include:

- current official low-water class;
- official recent development;
- one or two core historical reference values where clearly applicable.

### Recommended optional entities

Likely candidates for disabled-by-default entities include:

- static classification boundaries;
- dynamic classification boundaries;
- deciles;
- LFI;
- specialist climate indicators;
- detailed historical statistics;
- full derived time series.

### Entity categories

Diagnostic or specialist reference entities may use the Home Assistant
diagnostic entity category where appropriate.

A changing hydrological status should generally remain a normal sensor because
it may be used in dashboards and automations.

---

## 7.10 Naming principles

Derived-quantity names must clearly indicate whether they are:

- official NIWIS values;
- local Hydro Monitor calculations;
- historical metadata;
- current classifications;
- boundaries;
- climate indicators.

Examples of distinctions that must remain visible:

```text
Trend 7 days
```

versus:

```text
Official 7-day development
```

and:

```text
Historical NQ
```

versus:

```text
Current low-water class
```

Abbreviations such as MQ, MNQ, NM7Q and LFI should be retained where they are
official technical terms, but translations and documentation should explain
them for non-specialist users.

---

## 7.11 Automation use cases

Official derived quantities can support meaningful Home Assistant automations.

Examples include:

- notify when the official low-water class worsens;
- warn when a groundwater station crosses a dynamic classification boundary;
- trigger irrigation restrictions based on an official status;
- compare local rainfall or water use with hydrological conditions;
- create seasonal dashboards showing climate indicators;
- notify when a river leaves a low-water category.

Hydro Monitor must present these values accurately because users may base
real-world decisions on them.

The integration should avoid wording that implies regulatory authority unless
the official NIWIS value itself has that meaning.

---

## 7.12 Validation requirements

Every implemented derived quantity should have tests covering:

1. request construction;
2. endpoint selection;
3. parameter validation;
4. successful response mapping;
5. missing values;
6. malformed responses;
7. unsupported measurement types;
8. unit handling;
9. category handling;
10. diagnostics output.

Where possible, regression fixtures should use real public NIWIS responses
captured by the discovery tooling.

Tests should not merely verify that a value is returned.

They should verify that the value is mapped with the correct:

- quantity key;
- measurement type;
- unit;
- reference period;
- category or numeric result type.

---

## 7.13 Error handling

Failure of an optional derived endpoint should not make the raw observation
sensor unavailable.

The integration should distinguish:

- raw observation update failure;
- derived calculation failure;
- unsupported quantity;
- temporarily unavailable result;
- invalid provider response.

Possible architecture:

```text
Raw observation coordinator

Derived quantity coordinator or service
```

This separation prevents a specialist indicator from reducing the reliability
of the primary measurement.

---

## 7.14 Diagnostics

Derived diagnostics should eventually include:

- enabled quantity keys;
- endpoint family;
- last successful update;
- cached result age;
- result type;
- unit;
- period and reference period;
- last exception;
- supported measurement types.

Diagnostics should not include massive full time series unless explicitly
needed, because they can become difficult to review and share.

---

## 7.15 Proposed implementation order

The first implementation sprint should focus on quantities that provide high
user value and relatively clear semantics.

### Sprint 1 — Current hydrological classification

- official low-water class;
- category mapping;
- translations;
- one supported measurement type first;
- tests and diagnostics.

### Sprint 2 — Classification boundaries

- static boundaries;
- dynamic boundaries;
- relation between current value and boundaries;
- optional boundary entities.

### Sprint 3 — Official recent development

- official seven-day development;
- comparison with the existing local seven-day trend;
- clear naming to prevent confusion.

### Sprint 4 — Core historical statistics

- MQ;
- MNQ;
- NM7Q;
- NM30Q;
- measurement-type support matrix.

### Sprint 5 — Expert indicators

- LFI;
- deciles;
- additional specialist quantities.

### Sprint 6 — Climate indicators

- low-water days;
- monthly mean deviations;
- reference-period configuration;
- long-term charts.

This order intentionally begins with user-facing interpretation before exposing
large numbers of expert statistics.

---

## 7.16 Open questions

Before the derived-quantity implementation is considered stable, the following
questions must be resolved:

1. Which of the 43 quantities applies to each measurement type?
2. Which quantities are station-specific?
3. Which quantities require explicit reference periods?
4. Which units are returned for each quantity?
5. Which category codes or labels are official?
6. Are static boundaries versioned or periodically revised?
7. How frequently do dynamic boundaries change?
8. Can historical calculations be cached safely?
9. Which quantities should be enabled by default?
10. How should derived time series be represented in Home Assistant?
11. Should users be able to configure reference periods?
12. How should unsupported combinations be communicated in the config flow?

These questions should be answered from observed payloads and official sources,
not from abbreviation-based assumptions.

---

## 7.17 Core implementation principle

The derived-quantity implementation must follow one central rule:

> Preserve official NIWIS meaning while integrating it into Home Assistant in a
> provider-independent, testable and transparent way.

Hydro Monitor should not merely expose every value returned by the API.

It should expose values that are:

- understood;
- correctly mapped;
- appropriately named;
- useful to users;
- supported by tests;
- clearly distinguished from local calculations.

This principle will guide the next major development phase of the project.

---

# 8. Climate Indicators

## Overview

Hydrological observations describe the current state of a river, groundwater
body or spring.

Climate indicators describe something fundamentally different.

Rather than representing the current hydrological situation, they quantify
long-term developments by comparing observations against historical reference
periods.

Examples include

- increasing numbers of low-water days,
- long-term deviations from historical averages,
- changes in seasonal behaviour,
- climatic trends affecting groundwater recharge,
- long-term drought development.

These indicators allow Hydro Monitor to extend from real-time monitoring into
long-term environmental assessment.

They should therefore be regarded as complementary to observations rather than
replacements.

```text
Raw observation
        │
        ▼
Current hydrological state

Climate indicator
        │
        ▼
Long-term hydrological development
```

---

## 8.1 Current discovery status

The discovery process identified two dedicated climate-indicator endpoint
families within the public NIWIS API.

```text
berechneKlimaindikatorNiedrigwassertage

berechneKlimaindikatorMonatlicheAbweichungenMittelwert
```

Unlike most derived quantities, these endpoints appear to focus on climatic
evaluation rather than the interpretation of an individual observation.

Both endpoint families remain candidates for a dedicated implementation phase
following the core derived quantities.

---

## 8.2 Climate indicators versus observations

A common misconception is that climate indicators simply represent another
sensor value.

In reality they answer a completely different question.

| Observation | Climate Indicator |
|-------------|-------------------|
| What is happening today? | How has the situation evolved over many years? |
| Current measurement | Long-term evaluation |
| Frequently updated | Slowly changing |
| Station status | Climatic behaviour |

Consequently, climate indicators should not be refreshed with every observation
update.

---

## 8.3 Low-water days

The endpoint

```text
berechneKlimaindikatorNiedrigwassertage
```

appears to provide information relating to the occurrence of low-water days.

Although the exact response semantics still require verification, likely
applications include:

- annual number of low-water days;
- cumulative low-water duration;
- comparison with historical periods;
- drought trend analysis.

Hydro Monitor intentionally avoids assuming a precise definition until it has
been confirmed through observed payloads or official documentation.

---

## 8.4 Monthly mean deviations

The second discovered climate endpoint is

```text
berechneKlimaindikatorMonatlicheAbweichungenMittelwert
```

Its name suggests that NIWIS calculates deviations from historical monthly mean
values.

Potential outputs may include:

- absolute deviations;
- relative deviations;
- percentage anomalies;
- monthly trend series.

Before implementation the following aspects require verification:

- reference period;
- unit;
- aggregation interval;
- sign convention;
- update frequency.

---

## 8.5 Reference periods

Unlike observations, climate indicators depend heavily on the chosen reference
period.

Possible examples include:

```text
1961–1990

1991–2020

rolling 30-year reference
```

Hydro Monitor should preserve the reference period together with the calculated
indicator wherever this information is available.

Otherwise identical values calculated against different reference periods could
be interpreted incorrectly.

---

## 8.6 Temporal characteristics

Climate indicators evolve much more slowly than raw observations.

Typical update frequencies may include:

| Indicator | Typical update |
|------------|----------------|
| Observation | Daily |
| Low-water class | Daily |
| Climate indicator | Monthly or yearly |

Refreshing climate indicators together with every observation would therefore
produce unnecessary API traffic.

Dedicated update scheduling is recommended.

---

## 8.7 Home Assistant representation

Climate indicators should not necessarily be presented as ordinary sensor
entities.

Possible representations include:

- diagnostic entities;
- statistics entities;
- dashboard charts;
- yearly summaries;
- long-term trend cards.

The chosen representation should reflect their analytical nature rather than
their comparatively slow update cycle.

---

## 8.8 Future dashboard possibilities

Climate indicators open entirely new dashboard concepts.

Examples include:

- annual drought overview;
- comparison of several groundwater stations;
- seasonal development charts;
- historical trend visualisations;
- climate anomaly summaries.

These dashboards would complement the current real-time monitoring pages by
providing historical context.

---

## 8.9 Automation opportunities

Although climate indicators change infrequently, they may still trigger useful
automations.

Examples include:

- notify when a new annual low-water threshold is exceeded;
- warn about increasing groundwater deficits;
- create yearly reports;
- trigger irrigation recommendations based on long-term drought conditions.

Such automations should generally be informational rather than reactive.

---

## 8.10 Design principles

Climate indicators should follow the same architectural principles as the rest
of Hydro Monitor.

Specifically:

- preserve official NIWIS calculations;
- avoid local reimplementation;
- expose reference periods;
- distinguish observations from climatic assessments;
- support provider-independent models;
- remain fully testable.

By keeping climate indicators separate from both observations and standard
derived quantities, Hydro Monitor maintains a clear conceptual separation
between current hydrological state and long-term environmental development.

---

# 9. Architecture Decision Record

## Overview

Software architecture is shaped as much by rejected ideas as by implemented
solutions.

Throughout the development of Hydro Monitor, numerous alternative approaches
were evaluated.

This chapter documents the most important architectural decisions together with
their rationale.

Its purpose is not to justify the current implementation uncritically.

Instead, it records *why* particular trade-offs were accepted at the time they
were made.

Future contributors should understand these decisions before introducing major
architectural changes.

---

## ADR-001 — Provider-independent core models

### Decision

Introduce provider-independent models (`HydroStation` and
`HydroObservation`) instead of exposing NIWIS payloads throughout the
integration.

### Motivation

Hydro Monitor is intended to support additional hydrological providers beyond
NIWIS.

Allowing provider-specific payloads to reach the Home Assistant layer would
couple every future provider to entity implementations.

### Consequences

Advantages

- reusable entity layer;
- simpler testing;
- consistent behaviour across providers;
- easier future extensions.

Trade-offs

- additional mapping layer;
- slightly more implementation effort.

---

## ADR-002 — Separate stations from observations

### Decision

Model station metadata and observations independently.

### Motivation

Station information changes rarely.

Observation values change frequently.

Treating both as a single object would cause unnecessary updates and duplicate
large amounts of static information.

### Consequences

Advantages

- cleaner entities;
- lower update overhead;
- easier caching;
- better separation of responsibilities.

---

## ADR-003 — Dedicated metadata entities

### Decision

Expose station metadata as dedicated entities instead of primary sensor
attributes.

### Motivation

Early prototypes attached all metadata to the observation sensor.

This resulted in:

- oversized attribute dictionaries;
- duplicated information;
- poor discoverability;
- difficult localisation.

### Consequences

Advantages

- cleaner Home Assistant device pages;
- individual entity enable/disable;
- better localisation;
- improved long-term maintainability.

---

## ADR-004 — Defensive mapping

### Decision

Never assume NIWIS payloads are complete or perfectly consistent.

### Motivation

Discovery identified:

- placeholder values;
- optional metadata;
- varying measurement completeness;
- unknown quality flags.

### Consequences

Hydro Monitor always prefers

- partial data,
- transparent handling,
- unavailable values,

over silently guessing missing information.

---

## ADR-005 — Preserve unknown values

### Decision

Unknown provider values are preserved rather than interpreted.

Examples include

- quality flags;
- metadata;
- future endpoint fields.

### Motivation

Discarding unknown information would make future analysis impossible.

Guessing meanings would risk introducing incorrect behaviour.

### Consequences

Future versions can support newly documented values without breaking older
installations.

---

## ADR-006 — Discovery before implementation

### Decision

Perform systematic API discovery before implementing complex features.

### Motivation

Rather than implementing individual endpoints as they were encountered, Hydro
Monitor first analysed the complete public NIWIS API.

This produced:

- endpoint inventory;
- metadata inventory;
- derived quantity catalogue;
- quality analysis.

### Consequences

Implementation decisions are based on observed behaviour rather than isolated
examples.

---

## ADR-007 — Local calculations versus official calculations

### Decision

Clearly distinguish between

- locally calculated values;
- official NIWIS calculations.

### Motivation

A seven-day trend calculated from recent observations is fundamentally
different from an official NIWIS hydrological indicator.

Both should remain visible to users without creating confusion.

### Consequences

Naming, entities and documentation all distinguish between local calculations
and official derived quantities.

---

## ADR-008 — Provider modules remain Home Assistant independent

### Decision

Provider code should not depend on Home Assistant entities.

### Motivation

Separating provider logic from Home Assistant enables:

- isolated testing;
- future reuse;
- easier maintenance.

### Consequences

The provider layer can evolve independently of Home Assistant UI concepts.

---

## ADR-009 — Inventory-driven development

### Decision

Generate inventories describing the public API before implementing new
features.

### Motivation

Inventories provide:

- reproducibility;
- regression detection;
- offline analysis;
- technical documentation.

### Consequences

The inventory becomes part of the project's engineering process rather than a
temporary development artefact.

---

## ADR-010 — Documentation as architecture

### Decision

Treat documentation as part of the implementation rather than an afterthought.

### Motivation

Hydro Monitor relies heavily on reverse-engineered knowledge.

Without documentation, much of this knowledge would disappear over time.

### Consequences

The technical reference becomes an integral component of the project.

Major architectural changes should update both the implementation and this
document.

---

## Summary

The architecture of Hydro Monitor is intentionally conservative.

Whenever multiple implementation options existed, the project generally
preferred

- correctness over convenience;
- explicitness over implicit behaviour;
- maintainability over minimal code;
- provider independence over provider optimisation;
- transparency over hidden assumptions.

These principles have guided every major design decision and will continue to
shape future development.

---

# 10. Development Roadmap

## Overview

Hydro Monitor has been developed incrementally.

Rather than implementing every discovered NIWIS capability immediately, the
project intentionally progresses through clearly defined development phases.

Each phase establishes a stable technical foundation before introducing more
advanced hydrological functionality.

This strategy has several advantages:

- stable public releases;
- continuous test coverage;
- incremental architectural validation;
- reduced implementation risk;
- easier review of complex features.

The roadmap described below reflects the intended long-term direction of the
project.

It should be regarded as guidance rather than a fixed release contract.

---

## Phase 1 — Provider Foundation (Completed)

The first development phase established the provider architecture and all
fundamental building blocks required by future functionality.

Completed work includes:

- provider-independent models;
- NIWIS REST client;
- station discovery;
- configuration flow;
- observation processing;
- rolling statistics;
- local trend calculation;
- complete station metadata mapping;
- diagnostics;
- system health;
- automated testing;
- technical documentation.

This phase focused primarily on correctness and maintainability.

---

## Phase 2 — Official Hydrological Intelligence

The next phase introduces official NIWIS calculations.

Rather than relying exclusively on locally calculated values, Hydro Monitor
will expose officially derived hydrological information.

Initial objectives include:

- official low-water classifications;
- official development indicators;
- classification boundaries;
- selected historical reference values.

Throughout this phase, locally calculated trends will continue to exist.

Official NIWIS calculations and locally derived values will remain clearly
distinguishable.

---

## Phase 3 — Historical Hydrology

Following the implementation of official classifications, Hydro Monitor will
expand its support for historical hydrological statistics.

Potential examples include:

- MQ;
- MNQ;
- NM7Q;
- NM30Q;
- percentile values;
- deciles;
- historical comparison values.

These statistics provide users with valuable historical context that cannot be
derived from recent observations alone.

---

## Phase 4 — Climate Analytics

Once historical statistics are available, Hydro Monitor will extend into
long-term environmental analysis.

Potential features include:

- low-water day indicators;
- monthly climatic deviations;
- groundwater development trends;
- drought summaries;
- historical climate dashboards.

These capabilities move the project beyond current-state monitoring toward
climate-aware hydrological assessment.

---

## Phase 5 — Multi-Provider Architecture

Although NIWIS serves as the initial implementation, Hydro Monitor was designed
from the outset as a provider-independent platform.

Future providers may include:

- additional German federal states;
- neighbouring European countries;
- research institutions;
- public hydrological services.

New providers should integrate through the existing provider abstraction
without requiring changes to the Home Assistant entity layer.

---

## Phase 6 — Advanced Home Assistant Integration

Future Home Assistant integration may extend beyond individual sensors.

Potential improvements include:

- dedicated dashboards;
- map visualisations;
- comparison views;
- historical charts;
- summary cards;
- automation blueprints.

These features should build upon the existing provider-independent architecture
rather than introducing provider-specific presentation logic.

---

## Long-Term Vision

The long-term objective of Hydro Monitor is not simply to expose hydrological
measurements.

Instead, the project aims to become a comprehensive hydrological monitoring
platform for Home Assistant.

Core principles remain:

- provider independence;
- scientifically accurate representation;
- transparent processing;
- comprehensive metadata support;
- reproducible implementation;
- excellent documentation;
- maintainable architecture.

Future functionality should strengthen these principles rather than compromise
them for short-term convenience.

---

## Guiding Principle

Every future feature should satisfy three questions before implementation.

1. Does it improve hydrological understanding?

2. Can it be implemented in a provider-independent manner?

3. Can it be documented and tested to the same standard as the existing
architecture?

Only if all three questions can be answered positively should the feature
become part of Hydro Monitor.

This principle has guided the project from its first prototype and will
continue to define its future direction.

---

# 11. Known Limitations and Open Questions

## Overview

Hydro Monitor intentionally follows an evidence-based implementation strategy.

Only behaviour that has been verified through observation, repeated testing or
official documentation is implemented as a stable part of the provider.

Several aspects of the NIWIS API remain either undocumented or only partially
understood.

Rather than hiding these uncertainties, the project documents them explicitly.

This chapter records the current limitations together with the corresponding
research questions.

Documenting open questions helps future contributors distinguish between known
facts, observed behaviour and assumptions that still require validation.

---

## 11.1 Quality flags

Quality flags are preserved exactly as returned by NIWIS.

Observed examples include

```text
A
BfGAdded
```

However, the complete list of possible values and their official semantics have
not yet been verified.

Future work should establish:

- the complete quality-flag catalogue;
- the official meaning of each flag;
- whether flags indicate validation level, correction status or another
  quality concept;
- whether any flags should influence Home Assistant availability or diagnostics.

Until then, Hydro Monitor intentionally treats quality flags as informational
metadata only.

---

## 11.2 Placeholder values

Several technical placeholder values have been observed.

Examples include

```text
-777
-888
-999
-9999
```

These values are currently filtered before observation processing.

The exact distinction between the individual placeholder codes remains
undocumented.

Future work should determine whether they represent different technical
conditions such as:

- missing observation;
- invalid measurement;
- unavailable station;
- suppressed value.

Until verified, all known placeholders are treated uniformly.

---

## 11.3 Derived quantity applicability

The discovery process identified forty-three official derived quantities.

However, several questions remain open.

Examples include:

- Which quantities are available for every measurement type?
- Which quantities require additional parameters?
- Which quantities are station-specific?
- Which quantities are optional?
- Which quantities depend on historical reference periods?

These questions will be answered during the implementation of derived
quantities.

---

## 11.4 Climate indicators

The climate indicator endpoints have been discovered but not yet fully analysed.

Outstanding questions include:

- exact response schema;
- update frequency;
- reference periods;
- supported measurement types;
- returned units;
- intended interpretation.

Climate indicators therefore remain a dedicated future implementation phase.

---

## 11.5 Time-series semantics

The sampled NIWIS data has been sufficient for current observation processing.

Nevertheless, several aspects require additional investigation.

Examples include:

- duplicate observation dates;
- corrected observations;
- publication delays;
- sub-daily timestamps;
- observation revisions.

The current implementation deliberately avoids assumptions in these areas.

---

## 11.6 Historical reference periods

Several official calculations appear to rely on historical reference periods.

Important questions remain:

- Which reference periods are officially supported?
- Are reference periods configurable?
- Are historical values periodically recalculated?
- Are reference periods identical across measurement types?

Understanding these aspects will become increasingly important during the
implementation of climate indicators.

---

## 11.7 Additional providers

Hydro Monitor was designed for multiple providers from the beginning.

At present, however, only the Bavarian NIWIS provider has been implemented.

Future providers will help validate whether the provider-independent models are
sufficiently generic or require refinement.

This should be regarded as an architectural validation exercise rather than a
simple feature extension.

---

## 11.8 Performance

The current implementation has been designed for correctness rather than
large-scale deployments.

Potential future optimisation topics include:

- smarter caching;
- incremental updates;
- request batching;
- asynchronous discovery refresh;
- provider-specific optimisation.

Performance improvements should never compromise correctness or transparency.

---

## 11.9 Documentation

This technical reference is intended to evolve together with the project.

Future revisions should extend rather than replace existing knowledge.

Whenever implementation changes introduce new behaviour, the corresponding
sections of this document should be updated at the same time.

Maintaining documentation as part of the implementation process is considered
one of the project's architectural principles.

---

## Summary

Hydro Monitor deliberately records uncertainty instead of concealing it.

Unknown behaviour is documented.

Observed behaviour is preserved.

Only verified behaviour becomes part of the stable implementation.

This philosophy reduces the likelihood of introducing undocumented assumptions
while ensuring that future development is guided by evidence rather than
speculation.

---

# 12. Document History

## Purpose

This document is maintained alongside the Hydro Monitor source code.

Its history reflects the evolution of the provider architecture and the
knowledge gained during development.

Unlike the project CHANGELOG, this section records the evolution of the
technical reference itself.

---

## Version 0.1

Initial technical documentation.

Primary focus:

- provider architecture;
- NIWIS API structure;
- station discovery;
- observation retrieval.

---

## Version 0.2

Expansion of the provider documentation.

Added:

- provider-independent models;
- station metadata mapping;
- observation processing;
- quality handling;
- diagnostics;
- system health;
- testing strategy.

---

## Version 0.3.0-alpha

Major expansion of the technical reference.

Added:

- complete station metadata documentation;
- observation-processing pipeline;
- measurement-type analysis;
- reverse engineering methodology;
- derived quantity discovery;
- climate indicator analysis;
- architecture decision records;
- long-term development roadmap;
- implementation philosophy;
- known limitations.

This version represents the first comprehensive technical reference for the
Hydro Monitor NIWIS provider.

---

## Future revisions

Future versions of this document are expected to accompany the implementation
of:

- official derived quantities;
- classification boundaries;
- historical statistics;
- climate indicators;
- additional hydrological providers;
- advanced Home Assistant dashboards;
- analytics and reporting.

The document should continue to evolve incrementally together with the source
code.

---

## Closing Statement

Hydro Monitor is more than a Home Assistant integration.

It is an attempt to provide a provider-independent, scientifically sound and
well-documented platform for hydrological monitoring.

The implementation, the automated tests and this technical reference are
intended to evolve together.

Each supports the others.

By documenting not only the implementation but also the reasoning behind it,
the project aims to remain understandable, maintainable and extensible for many
years to come.
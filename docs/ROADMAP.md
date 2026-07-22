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

Potential providers:

- PegelOnline
- BAFU
- Rijkswaterstaat
- Environment Agency
- Others

Provider support should require only:

- API Client
- Mapper

Everything else should already exist.

Deliverable:

Provider-independent hydrology platform.

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
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

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
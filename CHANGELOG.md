# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

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
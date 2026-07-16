# Hydro Monitor

<p align="center">
  <img src="custom_components/hydro_monitor/brand/logo.png" alt="Hydro Monitor logo" width="220">
</p>

<p align="center">
  <strong>Hydrological monitoring for Home Assistant.</strong>
</p>

Hydro Monitor is a custom Home Assistant integration for public hydrological data. It is designed to help users discover nearby monitoring stations automatically and add groundwater, water-level, river-discharge, and spring-discharge data without having to know provider-specific station IDs.

> [!IMPORTANT]
> Hydro Monitor is currently under active development. NIWIS is the first supported provider.

## Features

- Native Home Assistant devices and sensors
- Automatic station discovery based on the Home Assistant location
- Groundwater level
- Water level
- River discharge
- Spring discharge
- Distance-based station sorting
- Home Assistant config flow
- NIWIS support
- HACS-compatible repository structure

## Vision

Hydro Monitor should become the central hydrological data integration for Home Assistant, automatically selecting the best public data source based on the user's location.

## Supported providers

| Provider | Status | Data |
|---|---|---|
| NIWIS | In development | Groundwater level, water level, discharge, spring discharge |

Additional providers may be added later without changing the core integration architecture.

## Installation

### Local development installation

1. Copy the folder:

   ```text
   custom_components/hydro_monitor
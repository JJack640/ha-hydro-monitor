"""Diagnostics support for Hydro Monitor."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import HydroMonitorConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: HydroMonitorConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a Hydro Monitor config entry."""
    runtime_data = entry.runtime_data
    station = runtime_data.station
    coordinator = runtime_data.coordinator
    observation = coordinator.data

    return {
        "config_entry": {
            "title": entry.title,
            "provider": station.provider,
            "station_id": station.station_id,
            "measurement_type": coordinator.measurement_type.value,
        },
        "station": {
            "name": station.name,
            "waterbody": station.waterbody,
            "operator": station.operator,
            "institution": station.institution,
            "source_url": station.source_url,
            "license": station.license_name,
            "supported_measurement_types": [
                measurement_type.value for measurement_type in station.measurement_types
            ],
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                str(coordinator.last_exception)
                if coordinator.last_exception is not None
                else None
            ),
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval is not None
                else None
            ),
        },
        "observation": (
            {
                "measurement_type": observation.measurement_type.value,
                "value": observation.value,
                "unit": observation.unit,
                "observed_on": (
                    observation.observed_on.isoformat()
                    if observation.observed_on is not None
                    else None
                ),
                "quality_flag": observation.quality_flag,
                "change_1d": observation.change_1d,
                "change_7d": observation.change_7d,
                "minimum_30d": observation.minimum_30d,
                "maximum_30d": observation.maximum_30d,
                "sample_count": observation.sample_count,
            }
            if observation is not None
            else None
        ),
    }

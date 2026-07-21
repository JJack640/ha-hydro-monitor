"""Provide system health information for Hydro Monitor."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(
    hass: HomeAssistant,
    register: system_health.RegisterSystemHealth,
) -> None:
    """Register Hydro Monitor system health information."""
    register.async_register_info(async_system_health_info)


async def async_system_health_info(
    hass: HomeAssistant,
) -> dict[str, Any]:
    """Return system health information for Hydro Monitor."""
    entries = hass.config_entries.async_entries(DOMAIN)
    loaded_entries = [entry for entry in entries if entry.runtime_data is not None]

    providers: set[str] = set()
    station_ids: set[str] = set()
    update_success_values: list[bool] = []
    update_intervals: set[float] = set()
    observation_dates: list[date] = []

    for entry in loaded_entries:
        runtime_data = entry.runtime_data
        station = runtime_data.station
        coordinator = runtime_data.coordinator

        providers.add(station.provider)
        station_ids.add(station.station_id)
        update_success_values.append(coordinator.last_update_success)

        if coordinator.update_interval is not None:
            update_intervals.add(coordinator.update_interval.total_seconds())

        observation = coordinator.data

        if observation is not None and observation.observed_on is not None:
            observation_dates.append(observation.observed_on)

    if not update_intervals:
        update_interval = None
    elif len(update_intervals) == 1:
        update_interval = f"{int(next(iter(update_intervals)) / 3600)} hours"
    else:
        update_interval = ", ".join(
            f"{int(interval / 3600)} h" for interval in sorted(update_intervals)
        )

    return {
        "Configured entries": len(entries),
        "Loaded entries": len(loaded_entries),
        "Configured stations": len(station_ids),
        "Providers": (
            ", ".join(provider.upper() for provider in sorted(providers))
            if providers
            else None
        ),
        "Last update successful": (
            all(update_success_values) if update_success_values else None
        ),
        "Update interval": update_interval,
        "Latest observation": (max(observation_dates) if observation_dates else None),
    }

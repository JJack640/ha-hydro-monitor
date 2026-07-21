"""Set up the Hydro Monitor integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_MEASUREMENT_TYPE, CONF_STATION_ID
from .coordinator import HydroMonitorCoordinator, async_get_station
from .models import HydroMeasurementType, HydroStation
from .providers.niwis.api import NiwisError

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(slots=True)
class HydroMonitorRuntimeData:
    """Store runtime data for a Hydro Monitor config entry."""

    station: HydroStation
    coordinator: HydroMonitorCoordinator


type HydroMonitorConfigEntry = ConfigEntry[HydroMonitorRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HydroMonitorConfigEntry,
) -> bool:
    """Set up Hydro Monitor from a config entry."""
    try:
        station = await async_get_station(
            hass,
            entry.data[CONF_STATION_ID],
        )
    except NiwisError as err:
        raise ConfigEntryNotReady(str(err)) from err

    measurement_type = HydroMeasurementType(entry.data[CONF_MEASUREMENT_TYPE])
    coordinator = HydroMonitorCoordinator(
        hass,
        entry,
        station,
        measurement_type,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = HydroMonitorRuntimeData(
        station=station,
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: HydroMonitorConfigEntry,
) -> bool:
    """Unload a Hydro Monitor config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

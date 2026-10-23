"""Coordinator that keeps one station's observation up to date."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .models import HydroMeasurementType, HydroObservation, HydroStation
from .providers import get_provider
from .providers.base import ObservationFetcher, ProviderError

_LOGGER = logging.getLogger(__name__)


class HydroMonitorCoordinator(DataUpdateCoordinator[HydroObservation]):
    """Polls the provider of one station for its current observation.

    Everything provider-specific lives in the provider's fetcher; this class
    only schedules it and maps provider failures to `UpdateFailed`.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        station: HydroStation,
        measurement_type: HydroMeasurementType,
    ) -> None:
        """Initialize the Hydro Monitor coordinator."""
        provider = get_provider(station.provider)

        self.station = station
        self.measurement_type = measurement_type
        self.fetcher: ObservationFetcher = provider.create_fetcher(
            hass, station, measurement_type
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"hydro_monitor_{station.station_id}_{measurement_type.value}",
            update_interval=provider.update_interval,
            config_entry=entry,
        )

    async def _async_update_data(self) -> HydroObservation:
        """Fetch the latest observation from the station's provider."""
        try:
            return await self.fetcher.async_update()
        except ProviderError as err:
            raise UpdateFailed(str(err)) from err

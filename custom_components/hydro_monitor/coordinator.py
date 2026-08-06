from __future__ import annotations

import logging
from dataclasses import replace

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL
from .models import HydroMeasurementType, HydroObservation, HydroStation
from .providers.niwis.api import NiwisClient, NiwisError
from .providers.niwis.const import (
    DERIVED_ENDPOINT_LOW_WATER_CLASS,
    DERIVED_REFERENCE_END_YEAR,
    DERIVED_REFERENCE_START_YEAR,
    DERIVED_YEAR_DEFINITION,
    HYDRO_TO_NIWIS_ENDPOINT,
    HYDRO_TO_NIWIS_LOW_WATER_CLASS_QUANTITY,
)
from .providers.niwis.mapper import (
    low_water_class_from_niwis,
    observation_from_niwis,
    station_from_niwis,
)

_LOGGER = logging.getLogger(__name__)


class HydroMonitorCoordinator(DataUpdateCoordinator[HydroObservation]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        station: HydroStation,
        measurement_type: HydroMeasurementType,
    ) -> None:
        """Initialize the Hydro Monitor coordinator."""
        self.station = station
        self.measurement_type = measurement_type
        self.client = NiwisClient(async_get_clientsession(hass))
        super().__init__(
            hass,
            _LOGGER,
            name=f"hydro_monitor_{station.station_id}_{measurement_type.value}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
            config_entry=entry,
        )

    async def _async_update_data(self) -> HydroObservation:
        """Fetch and map the latest NIWIS observation data."""
        try:
            series = await self.client.async_get_series(
                HYDRO_TO_NIWIS_ENDPOINT[self.measurement_type.value],
                self.station.station_id,
            )
        except NiwisError as err:
            raise UpdateFailed(str(err)) from err

        observation = observation_from_niwis(self.measurement_type, series)

        try:
            classification = await self.client.async_get_derived_result(
                DERIVED_ENDPOINT_LOW_WATER_CLASS,
                {
                    "abgeleiteteGroesse": HYDRO_TO_NIWIS_LOW_WATER_CLASS_QUANTITY[
                        self.measurement_type.value
                    ],
                    "messstelleNr": self.station.station_id,
                    "jahresdefinition": DERIVED_YEAR_DEFINITION,
                    "startJahr": str(DERIVED_REFERENCE_START_YEAR),
                    "endJahr": str(DERIVED_REFERENCE_END_YEAR),
                },
            )
        except NiwisError as err:
            _LOGGER.warning(
                "Could not fetch NIWIS low-water class for %s (%s): %s",
                self.station.station_id,
                self.measurement_type.value,
                err,
            )
            return replace(observation, low_water_class_error=str(err))

        low_water_class, low_water_class_error = low_water_class_from_niwis(
            classification
        )
        return replace(
            observation,
            low_water_class=low_water_class,
            low_water_class_error=low_water_class_error,
        )


async def async_get_station(
    hass: HomeAssistant,
    station_id: str,
) -> HydroStation:
    """Fetch a station definition from the NIWIS provider."""
    client = NiwisClient(async_get_clientsession(hass))
    station = await client.async_get_station(station_id)
    return station_from_niwis(station)

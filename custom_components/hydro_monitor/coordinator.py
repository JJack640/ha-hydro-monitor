from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL
from .models import (
    HydroLowWaterBoundaries,
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from .providers.niwis.api import NiwisClient, NiwisError
from .providers.niwis.const import (
    DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC,
    DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC,
    DERIVED_ENDPOINT_LOW_WATER_CLASS,
    DERIVED_REFERENCE_END_YEAR,
    DERIVED_REFERENCE_START_YEAR,
    DERIVED_YEAR_DEFINITION,
    HYDRO_TO_NIWIS_ENDPOINT,
    HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_DYNAMIC_QUANTITY,
    HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_STATIC_QUANTITY,
    HYDRO_TO_NIWIS_LOW_WATER_CLASS_QUANTITY,
)
from .providers.niwis.mapper import (
    dynamic_low_water_boundaries_from_niwis,
    low_water_class_from_niwis,
    observation_from_niwis,
    static_low_water_boundaries_from_niwis,
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
        self._dynamic_boundaries: HydroLowWaterBoundaries | None = None
        self._dynamic_boundaries_date: date | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"hydro_monitor_{station.station_id}_{measurement_type.value}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
            config_entry=entry,
        )

    def _reference_period_params(self, quantity: str) -> dict[str, str]:
        """Return the request params shared by all derived-quantity calls."""
        return {
            "abgeleiteteGroesse": quantity,
            "messstelleNr": self.station.station_id,
            "jahresdefinition": DERIVED_YEAR_DEFINITION,
            "startJahr": str(DERIVED_REFERENCE_START_YEAR),
            "endJahr": str(DERIVED_REFERENCE_END_YEAR),
        }

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
                self._reference_period_params(
                    HYDRO_TO_NIWIS_LOW_WATER_CLASS_QUANTITY[
                        self.measurement_type.value
                    ]
                ),
            )
        except NiwisError as err:
            _LOGGER.warning(
                "Could not fetch NIWIS low-water class for %s (%s): %s",
                self.station.station_id,
                self.measurement_type.value,
                err,
            )
            observation = replace(observation, low_water_class_error=str(err))
        else:
            low_water_class, low_water_class_raw, low_water_class_error = (
                low_water_class_from_niwis(classification)
            )
            observation = replace(
                observation,
                low_water_class=low_water_class,
                low_water_class_raw=low_water_class_raw,
                low_water_class_error=low_water_class_error,
            )

        static_boundaries = await self._async_fetch_static_boundaries()
        dynamic_boundaries = await self._async_fetch_dynamic_boundaries_cached()

        boundaries = replace(
            static_boundaries,
            dynamic_thresholds=dynamic_boundaries.dynamic_thresholds,
            dynamic_unit=dynamic_boundaries.dynamic_unit,
            dynamic_reference_date=dynamic_boundaries.dynamic_reference_date,
            dynamic_error=dynamic_boundaries.dynamic_error,
            classification_labels=(
                static_boundaries.classification_labels
                or dynamic_boundaries.classification_labels
            ),
            open_ended=(
                static_boundaries.open_ended
                if static_boundaries.open_ended is not None
                else dynamic_boundaries.open_ended
            ),
        )

        return replace(observation, boundaries=boundaries)

    async def _async_fetch_static_boundaries(self) -> HydroLowWaterBoundaries:
        """Fetch the official static low-water classification boundaries."""
        try:
            data = await self.client.async_get_derived_result(
                DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC,
                self._reference_period_params(
                    HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_STATIC_QUANTITY[
                        self.measurement_type.value
                    ]
                ),
            )
        except NiwisError as err:
            _LOGGER.warning(
                "Could not fetch NIWIS static low-water boundaries for %s (%s): %s",
                self.station.station_id,
                self.measurement_type.value,
                err,
            )
            return HydroLowWaterBoundaries(static_error=str(err))

        return static_low_water_boundaries_from_niwis(data)

    async def _async_fetch_dynamic_boundaries_cached(self) -> HydroLowWaterBoundaries:
        """Fetch the official dynamic low-water boundaries, cached per day.

        The underlying 366-row response is expensive and effectively only
        changes once per calendar day, so it is not worth fetching on every
        6h coordinator update. A failed fetch is not cached, so it is
        retried on the next update instead of pinning an error for the
        rest of the day.
        """
        today = date.today()
        if (
            self._dynamic_boundaries is not None
            and self._dynamic_boundaries_date == today
        ):
            return self._dynamic_boundaries

        try:
            data = await self.client.async_get_derived_result(
                DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC,
                self._reference_period_params(
                    HYDRO_TO_NIWIS_LOW_WATER_BOUNDARIES_DYNAMIC_QUANTITY[
                        self.measurement_type.value
                    ]
                ),
            )
        except NiwisError as err:
            _LOGGER.warning(
                "Could not fetch NIWIS dynamic low-water boundaries for %s (%s): %s",
                self.station.station_id,
                self.measurement_type.value,
                err,
            )
            return HydroLowWaterBoundaries(dynamic_error=str(err))

        boundaries = dynamic_low_water_boundaries_from_niwis(data, today)
        self._dynamic_boundaries = boundaries
        self._dynamic_boundaries_date = today
        return boundaries


async def async_get_station(
    hass: HomeAssistant,
    station_id: str,
) -> HydroStation:
    """Fetch a station definition from the NIWIS provider."""
    client = NiwisClient(async_get_clientsession(hass))
    station = await client.async_get_station(station_id)
    return station_from_niwis(station)

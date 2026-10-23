"""Fetch and assemble the current PEGELONLINE observation for one station."""

from __future__ import annotations

import logging
from dataclasses import replace

from ...models import HydroMeasurementType, HydroObservation, HydroStation
from .api import PegelonlineClient, PegelonlineError
from .const import HYDRO_TO_PEGELONLINE_TIMESERIES
from .mapper import level_state_from_pegelonline, observation_from_pegelonline

_LOGGER = logging.getLogger(__name__)


class PegelonlineObservationFetcher:
    """Produces the PEGELONLINE observation for one station and type.

    Two requests per update: the raw measurements of the last 31 days (the
    primary data, from which value, trends and extremes are calculated) and
    the time series with its unit and current measurement (the unit, and the
    MNW/MHW status of water levels).
    """

    def __init__(
        self,
        client: PegelonlineClient,
        station: HydroStation,
        measurement_type: HydroMeasurementType,
    ) -> None:
        """Initialize the fetcher."""
        self.client = client
        self.station = station
        self.measurement_type = measurement_type
        self._timeseries = HYDRO_TO_PEGELONLINE_TIMESERIES[measurement_type]
        # The unit of a series does not change; remembered so that a failing
        # second request does not take the primary value down with it.
        self._unit: str | None = None

    async def async_update(self) -> HydroObservation:
        """Fetch and map the latest PEGELONLINE observation.

        Raises PegelonlineError when the measurements are unavailable, or
        when the unit has never been learned and cannot be fetched now.
        """
        measurements = await self.client.async_get_measurements(
            self.station.station_id, self._timeseries
        )

        timeseries: dict | None = None
        timeseries_error: str | None = None

        try:
            timeseries = await self.client.async_get_timeseries(
                self.station.station_id, self._timeseries
            )
        except PegelonlineError as err:
            if self._unit is None:
                raise

            timeseries_error = str(err)
            _LOGGER.warning(
                "Could not fetch the PEGELONLINE time series for %s (%s): %s",
                self.station.station_id,
                self.measurement_type.value,
                err,
            )

        if timeseries is not None and isinstance(timeseries.get("unit"), str):
            self._unit = timeseries["unit"]

        observation = observation_from_pegelonline(
            self.measurement_type, measurements, self._unit
        )

        if self.measurement_type is not HydroMeasurementType.WATER_LEVEL:
            return observation

        if timeseries is None:
            return replace(observation, level_state_error=timeseries_error)

        level_state, level_state_raw = level_state_from_pegelonline(
            timeseries.get("currentMeasurement")
        )

        return replace(
            observation,
            level_state=level_state,
            level_state_raw=level_state_raw,
        )

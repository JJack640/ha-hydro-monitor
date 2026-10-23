"""The contract between Hydro Monitor and its data providers.

A provider is a public hydrological data service. The integration talks to
every provider through the same few operations and never imports a
provider's own code outside of `providers/<name>/`:

* find stations near a location (config flow; one catalog per flow),
* load one station by id (setup),
* create a fetcher that produces the current observation for one station and
  measurement type (coordinator).

Adding a provider means writing its client, mapper and fetcher, describing
it with a `ProviderDefinition` and registering it in `providers/__init__.py`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from homeassistant.core import HomeAssistant

from ..models import HydroMeasurementType, HydroObservation, HydroStation


class ProviderError(Exception):
    """Base class for errors raised by a data provider."""


class ObservationFetcher(Protocol):
    """Produces the current observation for one station and measurement type.

    A fetcher belongs to one config entry and may keep its own caches between
    updates. It raises `ProviderError` only when the primary measurement is
    unavailable; failures of optional extras are recorded on the returned
    observation instead.
    """

    async def async_update(self) -> HydroObservation:
        """Fetch and map the latest observation."""


class StationCatalog(Protocol):
    """Finds the stations of one provider near a location."""

    async def async_nearby_stations(
        self,
        measurement_type: HydroMeasurementType,
        *,
        latitude: float,
        longitude: float,
        limit: int | None = None,
    ) -> list[HydroStation]:
        """Return stations sorted by distance, with `distance_km` set.

        `limit=None` returns every station of that measurement type.
        """


type CatalogFactory = Callable[[HomeAssistant], StationCatalog]
type StationLoader = Callable[[HomeAssistant, str], Awaitable[HydroStation]]
type FetcherFactory = Callable[
    [HomeAssistant, HydroStation, HydroMeasurementType], ObservationFetcher
]


@dataclass(frozen=True, slots=True)
class ProviderDefinition:
    """Describes one data provider to the integration."""

    # Stored in config entries and prefixed to every unique id: never change.
    id: str
    name: str
    measurement_types: frozenset[HydroMeasurementType]
    update_interval: timedelta
    # Keys of the observation sensors this provider can fill. None means
    # every sensor the integration defines.
    observation_sensor_keys: frozenset[str] | None
    # (hass) -> catalog. Called once per config flow, so a catalog may cache
    # what it loads for the lifetime of that flow.
    create_catalog: CatalogFactory
    # async (hass, station_id) -> station
    get_station: StationLoader
    # (hass, station, measurement_type) -> fetcher
    create_fetcher: FetcherFactory

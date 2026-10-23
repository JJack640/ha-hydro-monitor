"""Provider-neutral station discovery across all data providers."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant

from ..models import HydroMeasurementType, HydroStation
from ..providers import get_provider, providers_for
from ..providers.base import ProviderError, StationCatalog
from .location import async_get_home_location

_LOGGER = logging.getLogger(__name__)


def _sort_key(station: HydroStation) -> tuple[float, str, str]:
    """Sort by distance, then name, then provider for a stable order."""
    return (
        station.distance_km if station.distance_km is not None else float("inf"),
        station.name.casefold(),
        station.provider,
    )


class StationDiscoveryService:
    """Discover nearby stations of every provider in one combined list."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the discovery service."""
        self._hass = hass
        self._catalogs: dict[str, StationCatalog] = {}

    def _catalog(self, provider_id: str) -> StationCatalog:
        """Return the catalog of a provider, created once per service."""
        if provider_id not in self._catalogs:
            self._catalogs[provider_id] = get_provider(provider_id).create_catalog(
                self._hass
            )

        return self._catalogs[provider_id]

    async def _async_collect(
        self,
        measurement_type: HydroMeasurementType,
        *,
        latitude: float,
        longitude: float,
        limit: int | None,
    ) -> list[HydroStation]:
        """Query every provider offering the type and merge the answers.

        One provider being down does not empty the list; only when every
        provider fails is the first error raised.
        """
        providers = providers_for(measurement_type)

        results = await asyncio.gather(
            *(
                self._catalog(provider.id).async_nearby_stations(
                    measurement_type,
                    latitude=latitude,
                    longitude=longitude,
                    limit=limit,
                )
                for provider in providers
            ),
            return_exceptions=True,
        )

        stations: list[HydroStation] = []
        errors: list[ProviderError] = []

        for provider, result in zip(providers, results, strict=True):
            if isinstance(result, ProviderError):
                _LOGGER.warning(
                    "Could not list %s stations for %s: %s",
                    provider.name,
                    measurement_type.value,
                    result,
                )
                errors.append(result)
            elif isinstance(result, BaseException):
                raise result
            else:
                stations.extend(result)

        if errors and len(errors) == len(providers):
            raise errors[0]

        stations.sort(key=_sort_key)

        return stations

    async def async_discover(
        self,
        measurement_type: HydroMeasurementType,
        *,
        limit: int = 10,
    ) -> list[HydroStation]:
        """Return the nearest stations for the requested measurement type."""
        location = await async_get_home_location(self._hass)

        stations = await self._async_collect(
            measurement_type,
            latitude=location.latitude,
            longitude=location.longitude,
            limit=limit,
        )

        return stations[:limit]

    async def async_search(
        self,
        measurement_type: HydroMeasurementType,
        query: str,
        *,
        limit: int = 10,
    ) -> list[HydroStation]:
        """Return stations whose name matches the query, sorted by distance."""
        location = await async_get_home_location(self._hass)

        all_stations = await self._async_collect(
            measurement_type,
            latitude=location.latitude,
            longitude=location.longitude,
            limit=None,
        )

        needle = query.strip().casefold()
        matches = [
            station for station in all_stations if needle in station.name.casefold()
        ]

        return matches[:limit]

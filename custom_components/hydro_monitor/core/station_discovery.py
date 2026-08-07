"""Provider-neutral station discovery service."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..models import HydroMeasurementType, HydroStation
from ..providers.niwis.catalog import NiwisCatalog
from .location import async_get_home_location


class StationDiscoveryService:
    """Discover nearby stations independent of the provider."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the discovery service."""
        self._hass = hass
        self._niwis = NiwisCatalog(hass)

    async def async_discover(
        self,
        measurement_type: HydroMeasurementType,
        *,
        limit: int = 10,
    ) -> list[HydroStation]:
        """Return the nearest stations for the requested measurement type."""
        location = await async_get_home_location(self._hass)

        return await self._niwis.async_nearby_stations(
            measurement_type,
            latitude=location.latitude,
            longitude=location.longitude,
            limit=limit,
        )

    async def async_search(
        self,
        measurement_type: HydroMeasurementType,
        query: str,
        *,
        limit: int = 10,
    ) -> list[HydroStation]:
        """Return stations whose name matches the query, sorted by distance."""
        location = await async_get_home_location(self._hass)

        all_stations = await self._niwis.async_nearby_stations(
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

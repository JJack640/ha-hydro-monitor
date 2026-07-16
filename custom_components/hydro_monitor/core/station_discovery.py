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

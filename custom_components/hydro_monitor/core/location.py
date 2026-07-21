"""Home Assistant location service."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant


@dataclass(frozen=True, slots=True)
class HomeLocation:
    """Represent the Home Assistant location."""

    latitude: float
    longitude: float
    elevation: float | None
    name: str


async def async_get_home_location(
    hass: HomeAssistant,
) -> HomeLocation:
    """Return the configured Home Assistant location."""
    return HomeLocation(
        latitude=hass.config.latitude,
        longitude=hass.config.longitude,
        elevation=hass.config.elevation,
        name=hass.config.location_name,
    )

"""The NIWIS provider definition."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ...const import DEFAULT_UPDATE_INTERVAL, PROVIDER_NIWIS
from ...models import HydroMeasurementType, HydroStation
from ..base import ProviderDefinition
from .api import NiwisClient
from .catalog import NiwisCatalog
from .fetcher import NiwisObservationFetcher
from .mapper import station_from_niwis


async def _async_get_station(hass: HomeAssistant, station_id: str) -> HydroStation:
    """Fetch a station definition from NIWIS."""
    client = NiwisClient(async_get_clientsession(hass))
    return station_from_niwis(await client.async_get_station(station_id))


def _create_fetcher(
    hass: HomeAssistant,
    station: HydroStation,
    measurement_type: HydroMeasurementType,
) -> NiwisObservationFetcher:
    """Create the fetcher for one config entry."""
    return NiwisObservationFetcher(
        NiwisClient(async_get_clientsession(hass)),
        station,
        measurement_type,
    )


NIWIS_PROVIDER = ProviderDefinition(
    id=PROVIDER_NIWIS,
    name="NIWIS",
    measurement_types=frozenset(HydroMeasurementType),
    update_interval=DEFAULT_UPDATE_INTERVAL,
    # NIWIS can fill every sensor the integration defines.
    observation_sensor_keys=None,
    create_catalog=NiwisCatalog,
    get_station=_async_get_station,
    create_fetcher=_create_fetcher,
)

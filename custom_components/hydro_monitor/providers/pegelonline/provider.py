"""The PEGELONLINE provider definition."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ...const import PROVIDER_PEGELONLINE
from ...models import HydroMeasurementType, HydroStation
from ..base import ProviderDefinition
from .api import PegelonlineClient
from .catalog import PegelonlineCatalog
from .const import HYDRO_TO_PEGELONLINE_TIMESERIES, UPDATE_INTERVAL
from .fetcher import PegelonlineObservationFetcher
from .mapper import station_from_pegelonline

# What a raw time series of water levels or discharges allows: the value, its
# trends and extremes, the age of the measurement, and the MNW/MHW status.
# None of NIWIS's classifications, deciles or reference statistics exist here.
OBSERVATION_SENSOR_KEYS = frozenset(
    {
        "value",
        "change_1d",
        "change_7d",
        "trend_state",
        "level_state",
        "maximum_30d",
        "minimum_30d",
        "last_measurement",
        "measurement_age",
    }
)


async def _async_get_station(hass: HomeAssistant, station_id: str) -> HydroStation:
    """Fetch a station definition from PEGELONLINE."""
    client = PegelonlineClient(async_get_clientsession(hass))
    return station_from_pegelonline(await client.async_get_station(station_id))


def _create_fetcher(
    hass: HomeAssistant,
    station: HydroStation,
    measurement_type: HydroMeasurementType,
) -> PegelonlineObservationFetcher:
    """Create the fetcher for one config entry."""
    return PegelonlineObservationFetcher(
        PegelonlineClient(async_get_clientsession(hass)),
        station,
        measurement_type,
    )


PEGELONLINE_PROVIDER = ProviderDefinition(
    id=PROVIDER_PEGELONLINE,
    name="PEGELONLINE",
    measurement_types=frozenset(HYDRO_TO_PEGELONLINE_TIMESERIES),
    update_interval=UPDATE_INTERVAL,
    observation_sensor_keys=OBSERVATION_SENSOR_KEYS,
    create_catalog=PegelonlineCatalog,
    get_station=_async_get_station,
    create_fetcher=_create_fetcher,
)

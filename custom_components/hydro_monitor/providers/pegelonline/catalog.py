"""PEGELONLINE station catalog handling."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util.location import distance

from ...const import CATALOG_CACHE_HOURS, DOMAIN
from ...models import HydroMeasurementType, HydroStation
from .api import PegelonlineClient, PegelonlineError
from .const import PEGELONLINE_TIMESERIES_TO_HYDRO
from .mapper import station_from_pegelonline

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION: Final = 1
_STORAGE_KEY: Final = f"{DOMAIN}.pegelonline_catalog"

# What the mapper reads of a station; the rest of the (large) response is
# not worth keeping in Home Assistant's storage.
_STATION_KEYS: Final = (
    "uuid",
    "number",
    "shortname",
    "longname",
    "km",
    "agency",
    "longitude",
    "latitude",
    "water",
)
_TIMESERIES_KEYS: Final = ("shortname", "unit", "equidistance", "gaugeZero")


def _trim(station: dict[str, Any]) -> dict[str, Any]:
    """Keep only the fields of a station (and its series) the mapper uses."""
    trimmed = {key: station[key] for key in _STATION_KEYS if key in station}
    trimmed["timeseries"] = [
        {key: item[key] for key in _TIMESERIES_KEYS if key in item}
        for item in station.get("timeseries") or []
        if isinstance(item, dict) and item.get("shortname") in PEGELONLINE_TIMESERIES_TO_HYDRO
    ]

    return trimmed


class PegelonlineCatalog:
    """Load, cache, filter, and sort PEGELONLINE stations.

    One request returns every station, so unlike the NIWIS catalog there are
    no per-station detail requests.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the PEGELONLINE catalog."""
        self._client = PegelonlineClient(async_get_clientsession(hass))
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, _STORAGE_KEY
        )
        self._stations: list[dict[str, Any]] = []
        self._loaded_at: datetime | None = None
        self._cache_loaded = False

    async def async_load_cache(self) -> None:
        """Load the cached station list once per catalog instance."""
        if self._cache_loaded:
            return

        cached = await self._store.async_load()
        self._cache_loaded = True

        if not cached:
            return

        stations = cached.get("stations")
        if isinstance(stations, list):
            self._stations = [item for item in stations if isinstance(item, dict)]

        raw_loaded_at = cached.get("loaded_at")
        if isinstance(raw_loaded_at, str):
            try:
                loaded_at = datetime.fromisoformat(raw_loaded_at)
            except ValueError:
                return

            self._loaded_at = (
                loaded_at if loaded_at.tzinfo else loaded_at.replace(tzinfo=UTC)
            )

    def _cache_is_fresh(self) -> bool:
        """Return whether the cached station list is still fresh."""
        if self._loaded_at is None or not self._stations:
            return False

        return datetime.now(UTC) - self._loaded_at < timedelta(
            hours=CATALOG_CACHE_HOURS
        )

    async def _async_refresh(self) -> None:
        """Download the station list and persist it.

        When the download fails but an older list is cached, that list is
        kept: stations rarely change, so a stale list beats no list.
        """
        try:
            stations = await self._client.async_get_stations()
        except PegelonlineError as err:
            if not self._stations:
                raise

            _LOGGER.warning(
                "Could not refresh the PEGELONLINE station list, using the "
                "cached one: %s",
                err,
            )
            return

        self._stations = [_trim(station) for station in stations]
        self._loaded_at = datetime.now(UTC)
        await self._store.async_save(
            {
                "loaded_at": self._loaded_at.isoformat(),
                "stations": self._stations,
            }
        )

    async def async_get_stations(
        self,
        measurement_type: HydroMeasurementType,
    ) -> list[HydroStation]:
        """Return mapped stations with coordinates supporting a type."""
        await self.async_load_cache()

        if not self._cache_is_fresh():
            await self._async_refresh()

        stations = [station_from_pegelonline(raw) for raw in self._stations]

        return [
            station
            for station in stations
            if measurement_type in station.measurement_types
            and station.latitude is not None
            and station.longitude is not None
        ]

    async def async_nearby_stations(
        self,
        measurement_type: HydroMeasurementType,
        *,
        latitude: float,
        longitude: float,
        limit: int | None = None,
    ) -> list[HydroStation]:
        """Return nearest stations for a measurement type.

        limit=None returns every station, sorted by distance.
        """
        stations = await self.async_get_stations(measurement_type)
        nearby = [
            replace(
                station,
                distance_km=round(
                    distance(latitude, longitude, station.latitude, station.longitude)
                    / 1000,
                    1,
                ),
            )
            for station in stations
        ]
        nearby.sort(
            key=lambda station: (
                station.distance_km
                if station.distance_km is not None
                else float("inf"),
                station.name.casefold(),
            )
        )

        return nearby if limit is None else nearby[:limit]

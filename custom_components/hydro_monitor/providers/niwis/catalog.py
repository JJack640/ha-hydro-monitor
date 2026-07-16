"""NIWIS station catalog handling."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util.location import distance

from ...const import CATALOG_CACHE_HOURS, DOMAIN
from ...models import HydroMeasurementType, HydroStation
from .api import NiwisClient, NiwisError
from .const import HYDRO_TO_NIWIS_TYPE
from .mapper import station_from_niwis

_STORAGE_VERSION = 1
_STORAGE_KEY = f"{DOMAIN}.niwis_catalog"
_MAX_PARALLEL_REQUESTS = 8


class NiwisCatalog:
    """Load, cache, filter, and sort NIWIS stations."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the NIWIS catalog."""
        self._client = NiwisClient(async_get_clientsession(hass))
        self._store: Store[dict[str, Any]] = Store(
            hass,
            _STORAGE_VERSION,
            _STORAGE_KEY,
        )
        self._details: dict[str, dict[str, Any]] = {}
        self._loaded_at: datetime | None = None
        self._cache_loaded = False

    async def async_load_cache(self) -> None:
        """Load cached NIWIS station details once per catalog instance."""
        if self._cache_loaded:
            return

        cached = await self._store.async_load()
        self._cache_loaded = True

        if not cached:
            return

        details = cached.get("details", {})
        if isinstance(details, dict):
            self._details = {
                station_id: station
                for station_id, station in details.items()
                if isinstance(station_id, str) and isinstance(station, dict)
            }

        raw_loaded_at = cached.get("loaded_at")
        if isinstance(raw_loaded_at, str):
            try:
                loaded_at = datetime.fromisoformat(raw_loaded_at)
            except ValueError:
                loaded_at = None

            if loaded_at is not None:
                if loaded_at.tzinfo is None:
                    loaded_at = loaded_at.replace(tzinfo=UTC)
                self._loaded_at = loaded_at

    async def _async_save_cache(self) -> None:
        """Persist station details in Home Assistant storage."""
        loaded_at = datetime.now(UTC)
        await self._store.async_save(
            {
                "loaded_at": loaded_at.isoformat(),
                "details": self._details,
            }
        )
        self._loaded_at = loaded_at

    def _cache_is_fresh(self) -> bool:
        """Return whether the catalog cache is still fresh."""
        if self._loaded_at is None:
            return False

        return datetime.now(UTC) - self._loaded_at < timedelta(
            hours=CATALOG_CACHE_HOURS
        )

    async def async_get_candidates(
        self,
        measurement_type: HydroMeasurementType,
    ) -> list[dict[str, Any]]:
        """Return raw catalog entries supporting a measurement type."""
        catalog = await self._client.async_get_station_catalog()
        niwis_type = HYDRO_TO_NIWIS_TYPE[measurement_type.value]

        return [
            station
            for station in catalog
            if niwis_type in (station.get("messgroesse") or [])
        ]

    async def _async_fetch_missing_details(
        self,
        candidates: list[dict[str, Any]],
    ) -> None:
        """Fetch metadata for stations not yet present in the cache."""
        missing = [
            station
            for station in candidates
            if station["messstelleNr"] not in self._details
        ]

        if not missing:
            return

        semaphore = asyncio.Semaphore(_MAX_PARALLEL_REQUESTS)

        async def fetch_one(station: dict[str, Any]) -> None:
            station_id = station["messstelleNr"]

            async with semaphore:
                try:
                    self._details[station_id] = await self._client.async_get_station(
                        station_id
                    )
                except NiwisError:
                    return

        await asyncio.gather(*(fetch_one(station) for station in missing))
        await self._async_save_cache()

    async def async_get_stations(
        self,
        measurement_type: HydroMeasurementType,
    ) -> list[HydroStation]:
        """Return mapped stations supporting a measurement type."""
        await self.async_load_cache()
        candidates = await self.async_get_candidates(measurement_type)

        await self._async_fetch_missing_details(candidates)

        stations: list[HydroStation] = []

        for candidate in candidates:
            details = self._details.get(candidate["messstelleNr"])
            if details is None:
                continue

            stations.append(station_from_niwis(details))

        return stations

    async def async_nearby_stations(
        self,
        measurement_type: HydroMeasurementType,
        *,
        latitude: float,
        longitude: float,
        limit: int,
    ) -> list[HydroStation]:
        """Return nearest stations for a measurement type."""
        stations = await self.async_get_stations(measurement_type)
        nearby: list[HydroStation] = []

        for station in stations:
            if station.latitude is None or station.longitude is None:
                continue

            station_distance = distance(
                latitude,
                longitude,
                station.latitude,
                station.longitude,
            )

            nearby.append(
                HydroStation(
                    provider=station.provider,
                    station_id=station.station_id,
                    name=station.name,
                    measurement_types=station.measurement_types,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    waterbody=station.waterbody,
                    operator=station.operator,
                    institution=station.institution,
                    source_url=station.source_url,
                    license_name=station.license_name,
                    distance_km=round(station_distance, 1),
                )
            )

        nearby.sort(
            key=lambda station: (
                station.distance_km
                if station.distance_km is not None
                else float("inf"),
                station.name.casefold(),
            )
        )

        return nearby[:limit]

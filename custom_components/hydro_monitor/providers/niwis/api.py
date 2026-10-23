from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any, ClassVar

from aiohttp import ClientError, ClientSession
from yarl import URL

from ..base import ProviderError
from .const import BASE_URL, KARTE_CACHE_TTL, KARTE_URL


class NiwisError(ProviderError):
    """Base exception for NIWIS API errors."""


class NiwisConnectionError(NiwisError):
    """Raised when the NIWIS API cannot be reached."""


class NiwisResponseError(NiwisError):
    """Raised when the NIWIS API returns an invalid response."""


class NiwisClient:
    # Shared by every client instance (one coordinator creates one client):
    # the NIWIS map-classification list is the same for all stations of a
    # measurement type, so devices refreshing around the same time reuse one
    # download instead of each fetching ~110 KB. Failures are never cached.
    _karte_cache: ClassVar[
        dict[tuple[str, str], tuple[float, list[dict[str, Any]]]]
    ] = {}

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    @classmethod
    def clear_karte_cache(cls) -> None:
        """Drop all cached map-classification lists (used by tests)."""
        cls._karte_cache.clear()

    async def _get_json(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
        *,
        base_url: str = BASE_URL,
    ) -> Any:
        try:
            async with self._session.get(
                URL(f"{base_url}/{endpoint}"),
                params=params,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Home Assistant Hydro Monitor/0.3.1",
                },
                timeout=45,
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (ClientError, TimeoutError) as err:
            raise NiwisConnectionError(str(err)) from err
        except ValueError as err:
            raise NiwisResponseError("Invalid JSON") from err

    async def async_get_station_catalog(self) -> list[dict[str, Any]]:
        data = await self._get_json("messstelle")
        if not isinstance(data, list):
            raise NiwisResponseError("Catalog is not a list")
        return [x for x in data if isinstance(x, dict) and x.get("messstelleNr")]

    async def async_get_derived_quantities(
        self,
    ) -> list[dict[str, Any]]:
        """Return the available NIWIS derived quantities."""
        data = await self._get_json("abgeleiteteGroesse")

        if not isinstance(data, list):
            raise NiwisResponseError("Derived quantities response is not a list")

        return [
            item
            for item in data
            if isinstance(item, dict)
            and item.get("abgeleiteteGroesse")
            and item.get("endpunkt")
        ]

    async def async_get_derived_result(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """Return one result from a NIWIS derived-quantity endpoint."""
        return await self._get_json(
            endpoint,
            params=params,
        )

    async def async_get_karte_stations(
        self, messgroesse: str, klassifikationsart: str
    ) -> list[dict[str, Any]]:
        """Return NIWIS's map classification list for one measurement type.

        One entry per station (nummer, niedrigwasserKlasse, entwicklung,
        pegelUnterGlw, ...), cached for KARTE_CACHE_TTL seconds. See the
        KARTE_URL comment in const.py for why the current low-water class
        comes from here.
        """
        key = (messgroesse, klassifikationsart)
        cached = self._karte_cache.get(key)
        if cached is not None and time.monotonic() - cached[0] < KARTE_CACHE_TTL:
            return cached[1]

        data = await self._get_json(
            f"messstelle/{messgroesse}",
            {"klassifikationsart": klassifikationsart},
            base_url=KARTE_URL,
        )
        if not isinstance(data, list):
            raise NiwisResponseError("Map classification response is not a list")

        stations = [x for x in data if isinstance(x, dict)]
        self._karte_cache[key] = (time.monotonic(), stations)
        return stations

    async def async_get_station(self, station_id: str) -> dict[str, Any]:
        data = await self._get_json("stammdaten", {"messstelleNr": station_id})
        if isinstance(data, list):
            data = data[0] if data else None
        if not isinstance(data, dict) or not data.get("messstelleNr"):
            raise NiwisResponseError("Station not found")
        return data

    async def async_get_series(
        self, endpoint: str, station_id: str, days: int = 30
    ) -> list[dict[str, Any]]:
        today = date.today()
        start = today - timedelta(days=days)
        data = await self._get_json(
            endpoint,
            {
                "messstelleNr": station_id,
                "von": start.isoformat(),
                "bis": today.isoformat(),
            },
        )
        if not isinstance(data, list):
            raise NiwisResponseError("Series is not a list")
        return [x for x in data if isinstance(x, dict)]

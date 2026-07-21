from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from aiohttp import ClientError, ClientSession
from yarl import URL

from .const import BASE_URL


class NiwisError(Exception):
    """Base exception for NIWIS API errors."""


class NiwisConnectionError(NiwisError):
    """Raised when the NIWIS API cannot be reached."""


class NiwisResponseError(NiwisError):
    """Raised when the NIWIS API returns an invalid response."""


class NiwisClient:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def _get_json(
        self, endpoint: str, params: dict[str, str] | None = None
    ) -> Any:
        try:
            async with self._session.get(
                URL(f"{BASE_URL}/{endpoint}"),
                params=params,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Home Assistant Hydro Monitor/0.3.0-alpha2",
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

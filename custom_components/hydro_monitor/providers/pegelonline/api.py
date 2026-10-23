"""HTTP client for the PEGELONLINE REST API v2."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession
from yarl import URL

from ..base import ProviderError
from .const import (
    BASE_URL,
    HISTORY_PERIOD,
    REQUEST_TIMEOUT_SECONDS,
    STATIONS_ENDPOINT,
)

# No version on purpose: it would go stale (the NIWIS client's did).
USER_AGENT = "Home Assistant Hydro Monitor"


class PegelonlineError(ProviderError):
    """Base exception for PEGELONLINE API errors."""


class PegelonlineConnectionError(PegelonlineError):
    """Raised when the PEGELONLINE API cannot be reached or answers an error."""


class PegelonlineResponseError(PegelonlineError):
    """Raised when the PEGELONLINE API returns an unusable response."""


class PegelonlineClient:
    """Fetch stations and measurements from PEGELONLINE."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client."""
        self._session = session

    async def _get_json(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        try:
            async with self._session.get(
                URL(f"{BASE_URL}/{path}"),
                params=params,
                headers={
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (ClientError, TimeoutError) as err:
            raise PegelonlineConnectionError(str(err)) from err
        except ValueError as err:
            raise PegelonlineResponseError("Invalid JSON") from err

    async def async_get_stations(self) -> list[dict[str, Any]]:
        """Return all stations with their time series (one request)."""
        data = await self._get_json(
            STATIONS_ENDPOINT, {"includeTimeseries": "true"}
        )

        if not isinstance(data, list):
            raise PegelonlineResponseError("Station list is not a list")

        return [item for item in data if isinstance(item, dict) and item.get("uuid")]

    async def async_get_station(self, station_id: str) -> dict[str, Any]:
        """Return one station with its time series."""
        data = await self._get_json(
            f"stations/{station_id}.json", {"includeTimeseries": "true"}
        )

        if not isinstance(data, dict) or not data.get("uuid"):
            raise PegelonlineResponseError("Station response is not a station")

        return data

    async def async_get_timeseries(
        self, station_id: str, timeseries: str
    ) -> dict[str, Any]:
        """Return a time series with its unit and current measurement.

        The current measurement carries the MNW/MHW status of water levels.
        """
        data = await self._get_json(
            f"stations/{station_id}/{timeseries}.json",
            {"includeCurrentMeasurement": "true"},
        )

        if not isinstance(data, dict):
            raise PegelonlineResponseError("Time series response is not an object")

        return data

    async def async_get_measurements(
        self, station_id: str, timeseries: str
    ) -> list[dict[str, Any]]:
        """Return about 31 days of raw measurements, oldest first."""
        data = await self._get_json(
            f"stations/{station_id}/{timeseries}/measurements.json",
            {"start": HISTORY_PERIOD},
        )

        if not isinstance(data, list):
            raise PegelonlineResponseError("Measurements are not a list")

        return [item for item in data if isinstance(item, dict)]

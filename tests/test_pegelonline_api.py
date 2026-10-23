"""Tests for the PEGELONLINE API client."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientError, ClientResponseError

from custom_components.hydro_monitor.providers.base import ProviderError
from custom_components.hydro_monitor.providers.pegelonline.api import (
    USER_AGENT,
    PegelonlineClient,
    PegelonlineConnectionError,
    PegelonlineError,
    PegelonlineResponseError,
)
from tests import pegelonline_fixtures as fixtures

BASE = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"


class _FakeResponse:
    """Minimal async-context-manager stand-in for an aiohttp response."""

    def __init__(self, payload: Any, status_error: Exception | None = None) -> None:
        self._payload = payload
        self._status_error = status_error

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    async def json(self, content_type: str | None = None) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeSession:
    """Records every GET and replays queued responses."""

    def __init__(self, *responses: Any) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: object, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": str(url), **kwargs})
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, _FakeResponse):
            return response
        return _FakeResponse(response)


def test_errors_are_provider_errors() -> None:
    """Test generic code can catch PEGELONLINE failures as ProviderError."""
    for error in (
        PegelonlineError,
        PegelonlineConnectionError,
        PegelonlineResponseError,
    ):
        assert issubclass(error, ProviderError)


@pytest.mark.asyncio
async def test_station_list_request() -> None:
    """Test one request for all stations, with their time series."""
    session = _FakeSession([fixtures.station(fixtures.KAUB)])

    stations = await PegelonlineClient(session).async_get_stations()

    assert [s["uuid"] for s in stations] == [fixtures.KAUB]
    (call,) = session.calls
    assert call["url"] == f"{BASE}/stations.json"
    assert call["params"] == {"includeTimeseries": "true"}


@pytest.mark.asyncio
async def test_requests_identify_the_integration() -> None:
    """Test headers: JSON, a stable user agent without a version, a timeout."""
    session = _FakeSession([])

    await PegelonlineClient(session).async_get_stations()

    (call,) = session.calls
    assert call["headers"] == {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    assert call["timeout"] == 45
    assert not any(character.isdigit() for character in USER_AGENT)


@pytest.mark.asyncio
async def test_station_list_drops_entries_that_are_not_stations() -> None:
    """Test a malformed entry does not take the whole list down."""
    good = {"uuid": "u1", "longname": "A"}
    session = _FakeSession([good, "text", None, {"longname": "no id"}, {"uuid": ""}])

    assert await PegelonlineClient(session).async_get_stations() == [good]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"uuid": "u1"}, "text", None, 3])
async def test_station_list_must_be_a_list(payload: object) -> None:
    """Test a changed response shape is reported, not silently emptied."""
    with pytest.raises(PegelonlineResponseError):
        await PegelonlineClient(_FakeSession(payload)).async_get_stations()


@pytest.mark.asyncio
async def test_single_station_request() -> None:
    """Test one station by id, with its time series."""
    raw = fixtures.station(fixtures.KAUB)
    session = _FakeSession(raw)

    assert await PegelonlineClient(session).async_get_station(fixtures.KAUB) == raw
    (call,) = session.calls
    assert call["url"] == f"{BASE}/stations/{fixtures.KAUB}.json"
    assert call["params"] == {"includeTimeseries": "true"}


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [[], "text", {}, {"uuid": ""}, None])
async def test_single_station_must_be_a_station(payload: object) -> None:
    """Test a response that is not a station is rejected."""
    with pytest.raises(PegelonlineResponseError):
        await PegelonlineClient(_FakeSession(payload)).async_get_station("u1")


@pytest.mark.asyncio
async def test_timeseries_request_asks_for_the_current_measurement() -> None:
    """Test the series comes with unit and current measurement in one request."""
    raw = fixtures.timeseries(fixtures.KAUB, "W")
    session = _FakeSession(raw)

    assert (
        await PegelonlineClient(session).async_get_timeseries(fixtures.KAUB, "W")
        == raw
    )
    (call,) = session.calls
    assert call["url"] == f"{BASE}/stations/{fixtures.KAUB}/W.json"
    assert call["params"] == {"includeCurrentMeasurement": "true"}


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [[], "text", None])
async def test_timeseries_must_be_an_object(payload: object) -> None:
    """Test a time series response of the wrong shape is rejected."""
    with pytest.raises(PegelonlineResponseError):
        await PegelonlineClient(_FakeSession(payload)).async_get_timeseries("u1", "W")


@pytest.mark.asyncio
async def test_measurements_request_covers_31_days() -> None:
    """Test the history request: one call with the 31-day period."""
    raw = fixtures.measurements(fixtures.KAUB, "W")
    session = _FakeSession(raw)

    assert (
        await PegelonlineClient(session).async_get_measurements(fixtures.KAUB, "W")
        == raw
    )
    (call,) = session.calls
    assert call["url"] == f"{BASE}/stations/{fixtures.KAUB}/W/measurements.json"
    assert call["params"] == {"start": "P31D"}


@pytest.mark.asyncio
async def test_measurements_drop_entries_that_are_not_objects() -> None:
    """Test a stray entry in the list is dropped."""
    point = {"timestamp": "2026-10-23T13:00:00+02:00", "value": 1.0}
    session = _FakeSession([point, 5, None, "x"])

    assert await PegelonlineClient(session).async_get_measurements("u1", "W") == [point]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, "text", None])
async def test_measurements_must_be_a_list(payload: object) -> None:
    """Test a response of the wrong shape is rejected."""
    with pytest.raises(PegelonlineResponseError):
        await PegelonlineClient(_FakeSession(payload)).async_get_measurements("u1", "W")


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ClientError("down"), TimeoutError()])
async def test_network_failures_are_connection_errors(error: Exception) -> None:
    """Test unreachable service and timeouts."""
    with pytest.raises(PegelonlineConnectionError):
        await PegelonlineClient(_FakeSession(error)).async_get_stations()


@pytest.mark.asyncio
async def test_http_errors_are_connection_errors() -> None:
    """Test an HTTP error status, such as the service's real 404 for a station."""
    not_found = fixtures.errors()["unknown_station_measurements"]
    assert not_found["status"] == 404
    request_info = MagicMock()
    request_info.real_url = f"{BASE}/{not_found['path']}"
    error = ClientResponseError(
        request_info, (), status=404, message=not_found["body"]["message"]
    )

    with pytest.raises(PegelonlineConnectionError, match="Timeseries does not exist"):
        await PegelonlineClient(
            _FakeSession(_FakeResponse([], status_error=error))
        ).async_get_measurements("00000000-0000-0000-0000-000000000000", "W")


@pytest.mark.asyncio
async def test_invalid_json_is_a_response_error() -> None:
    """Test a body that is not JSON."""
    with pytest.raises(PegelonlineResponseError, match="Invalid JSON"):
        await PegelonlineClient(
            _FakeSession(_FakeResponse(ValueError("bad json")))
        ).async_get_stations()

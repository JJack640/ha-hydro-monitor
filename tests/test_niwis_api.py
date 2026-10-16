"""Tests for the NIWIS API client's map-classification (karte) request + cache."""

from typing import Any
from unittest.mock import patch

import pytest
from aiohttp import ClientError

from custom_components.hydro_monitor.providers.niwis.api import (
    NiwisClient,
    NiwisConnectionError,
    NiwisResponseError,
)
from custom_components.hydro_monitor.providers.niwis.const import KARTE_CACHE_TTL


class _FakeResponse:
    """Minimal async-context-manager stand-in for an aiohttp response."""

    def __init__(self, payload: Any) -> None:
        self._payload = payload

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self, content_type: str | None = None) -> Any:
        return self._payload


class _FakeSession:
    """Records every GET and replays queued payloads (an Exception is raised)."""

    def __init__(self, *payloads: Any) -> None:
        self._payloads = list(payloads)
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    def get(self, url: object, **kwargs: Any) -> _FakeResponse:
        self.calls.append((str(url), kwargs.get("params")))
        payload = self._payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return _FakeResponse(payload)


@pytest.fixture(autouse=True)
def _clear_karte_cache() -> None:
    """The cache is class-level; isolate every test from the others."""
    NiwisClient.clear_karte_cache()


_STATIONS = [{"nummer": "A", "niedrigwasserKlasse": "NIEDRIG"}]


@pytest.mark.asyncio
async def test_karte_request_url_and_params() -> None:
    """Test the exact URL (karte base, not daten) and the required art parameter."""
    session = _FakeSession(_STATIONS)

    result = await NiwisClient(session).async_get_karte_stations(
        "ABFLUSS", "DYNAMISCH"
    )

    assert result == _STATIONS
    assert session.calls == [
        (
            "https://niwis-online.de/api/karte/messstelle/ABFLUSS",
            {"klassifikationsart": "DYNAMISCH"},
        )
    ]


@pytest.mark.asyncio
async def test_karte_second_call_within_ttl_is_a_cache_hit() -> None:
    """Test that a repeat call inside the TTL does not hit the network again."""
    session = _FakeSession(_STATIONS)
    client = NiwisClient(session)

    with patch(
        "custom_components.hydro_monitor.providers.niwis.api.time.monotonic",
        side_effect=[1000.0, 1000.0 + KARTE_CACHE_TTL - 1],
    ):
        first = await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH")
        second = await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH")

    assert first == second == _STATIONS
    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_karte_cache_is_shared_between_client_instances() -> None:
    """Test that devices (one client each) reuse the same download."""
    session = _FakeSession(_STATIONS)

    await NiwisClient(session).async_get_karte_stations("ABFLUSS", "DYNAMISCH")
    await NiwisClient(session).async_get_karte_stations("ABFLUSS", "DYNAMISCH")

    assert len(session.calls) == 1


@pytest.mark.asyncio
async def test_karte_refetches_after_ttl_expiry() -> None:
    """Test that an expired entry is downloaded again."""
    fresh = [{"nummer": "A", "niedrigwasserKlasse": "SEHR_NIEDRIG"}]
    session = _FakeSession(_STATIONS, fresh)
    client = NiwisClient(session)

    with patch(
        "custom_components.hydro_monitor.providers.niwis.api.time.monotonic",
        side_effect=[1000.0, 1000.0 + KARTE_CACHE_TTL + 1, 1000.0 + KARTE_CACHE_TTL + 1],
    ):
        await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH")
        second = await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH")

    assert second == fresh
    assert len(session.calls) == 2


@pytest.mark.asyncio
async def test_karte_cache_is_keyed_per_measurement_type_and_art() -> None:
    """Test that other types / classification arts are separate cache entries."""
    session = _FakeSession(_STATIONS, _STATIONS, _STATIONS)
    client = NiwisClient(session)

    await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH")
    await client.async_get_karte_stations("WASSERSTAND", "DYNAMISCH")
    await client.async_get_karte_stations("ABFLUSS", "STATISCH")

    assert len(session.calls) == 3


@pytest.mark.asyncio
async def test_karte_failure_is_not_cached() -> None:
    """Test that a failed download is retried instead of pinning the error."""
    session = _FakeSession(ClientError("boom"), _STATIONS)
    client = NiwisClient(session)

    with pytest.raises(NiwisConnectionError):
        await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH")

    assert await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH") == _STATIONS
    assert len(session.calls) == 2


@pytest.mark.parametrize("payload", [{}, "oops", None, 42])
@pytest.mark.asyncio
async def test_karte_non_list_response_raises_and_is_not_cached(
    payload: object,
) -> None:
    """Test that a malformed (non-list) response is rejected and not cached."""
    session = _FakeSession(payload, _STATIONS)
    client = NiwisClient(session)

    with pytest.raises(NiwisResponseError):
        await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH")

    assert await client.async_get_karte_stations("ABFLUSS", "DYNAMISCH") == _STATIONS


@pytest.mark.asyncio
async def test_karte_drops_non_dict_entries() -> None:
    """Test that junk entries in the list are filtered out."""
    session = _FakeSession(["junk", None, _STATIONS[0]])

    result = await NiwisClient(session).async_get_karte_stations(
        "ABFLUSS", "DYNAMISCH"
    )

    assert result == _STATIONS

"""Tests for the PEGELONLINE station catalog."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType
from custom_components.hydro_monitor.providers.pegelonline.api import (
    PegelonlineConnectionError,
)
from custom_components.hydro_monitor.providers.pegelonline.catalog import (
    PegelonlineCatalog,
    _trim,
)
from tests import pegelonline_fixtures as fixtures

WATER_LEVEL = HydroMeasurementType.WATER_LEVEL
DISCHARGE = HydroMeasurementType.DISCHARGE


def _catalog(
    *,
    stations: list | Exception | None = None,
    cached: dict | None = None,
) -> PegelonlineCatalog:
    """Build a catalog around a fake client and store, without __init__."""
    catalog = PegelonlineCatalog.__new__(PegelonlineCatalog)
    catalog._client = MagicMock()
    if isinstance(stations, Exception):
        catalog._client.async_get_stations = AsyncMock(side_effect=stations)
    else:
        catalog._client.async_get_stations = AsyncMock(return_value=stations or [])
    catalog._store = MagicMock()
    catalog._store.async_load = AsyncMock(return_value=cached)
    catalog._store.async_save = AsyncMock()
    catalog._stations = []
    catalog._loaded_at = None
    catalog._cache_loaded = False
    return catalog


def _all_samples() -> list[dict]:
    return list(fixtures.stations_sample().values())


@pytest.mark.asyncio
async def test_stations_are_filtered_by_type_and_coordinates() -> None:
    """Test only mappable stations of the requested type are offered."""
    catalog = _catalog(stations=_all_samples())

    water = {s.station_id for s in await catalog.async_get_stations(WATER_LEVEL)}
    discharge = {s.station_id for s in await catalog.async_get_stations(DISCHARGE)}

    assert fixtures.KAUB in water
    assert fixtures.AHLDEN in water
    # No coordinates: cannot be sorted by distance, so not offered.
    assert fixtures.DORDRECHT not in water
    assert fixtures.PRELOUC not in discharge
    # Only offers other series: no type at all.
    assert not any(station.startswith(fixtures.ABBENFLETH) for station in water | discharge)
    # Water-level-only gauges are no discharge stations.
    assert discharge == {fixtures.KAUB}


@pytest.mark.asyncio
async def test_nearby_stations_are_sorted_by_distance() -> None:
    """Test the nearest first, with the distance set."""
    catalog = _catalog(stations=_all_samples())

    # Right next to Kaub (Rhine) - far from the Hamburg and Hamm gauges.
    result = await catalog.async_nearby_stations(
        WATER_LEVEL, latitude=50.08, longitude=7.77, limit=None
    )

    assert result[0].station_id == fixtures.KAUB
    assert result[0].distance_km is not None and result[0].distance_km < 1
    distances = [station.distance_km for station in result]
    assert distances == sorted(distances)
    assert all(station.provider == "pegelonline" for station in result)


@pytest.mark.asyncio
async def test_nearby_stations_respect_the_limit() -> None:
    """Test a limit keeps only the nearest."""
    catalog = _catalog(stations=_all_samples())

    result = await catalog.async_nearby_stations(
        WATER_LEVEL, latitude=50.08, longitude=7.77, limit=2
    )

    assert len(result) == 2
    assert result[0].station_id == fixtures.KAUB


@pytest.mark.asyncio
async def test_station_list_is_downloaded_once_per_fresh_cache() -> None:
    """Test a second lookup within the cache time does not download again."""
    catalog = _catalog(stations=_all_samples())

    await catalog.async_get_stations(WATER_LEVEL)
    await catalog.async_get_stations(DISCHARGE)

    catalog._client.async_get_stations.assert_awaited_once()


@pytest.mark.asyncio
async def test_downloaded_list_is_persisted_trimmed() -> None:
    """Test what is stored: the fields the mapper uses, only W and Q series."""
    catalog = _catalog(stations=_all_samples())

    await catalog.async_get_stations(WATER_LEVEL)

    (saved,) = catalog._store.async_save.await_args.args
    assert datetime.fromisoformat(saved["loaded_at"]).tzinfo is not None
    kaub = next(s for s in saved["stations"] if s["uuid"] == fixtures.KAUB)
    assert set(kaub) <= {
        "uuid", "number", "shortname", "longname", "km", "agency",
        "longitude", "latitude", "water", "timeseries",
    }  # fmt: skip
    assert {item["shortname"] for item in kaub["timeseries"]} == {"W", "Q"}
    assert "currentMeasurement" not in kaub["timeseries"][0]


def test_trim_drops_other_series() -> None:
    """Test water temperature and the like are not kept."""
    raw = {
        "uuid": "u1",
        "timeseries": [
            {"shortname": "W", "unit": "cm"},
            {"shortname": "WT", "unit": "°C"},
            "garbage",
        ],
        "voiceServiceNumber": "+49 ...",
    }

    assert _trim(raw) == {"uuid": "u1", "timeseries": [{"shortname": "W", "unit": "cm"}]}


@pytest.mark.asyncio
async def test_fresh_stored_list_is_used_without_a_download() -> None:
    """Test a persisted list younger than the cache time avoids the request."""
    stored = [_trim(s) for s in _all_samples()]
    loaded_at = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    catalog = _catalog(cached={"loaded_at": loaded_at, "stations": stored})

    result = await catalog.async_get_stations(WATER_LEVEL)

    assert fixtures.KAUB in {s.station_id for s in result}
    catalog._client.async_get_stations.assert_not_awaited()


@pytest.mark.asyncio
async def test_old_stored_list_is_refreshed() -> None:
    """Test a persisted list older than 24 h is downloaded again."""
    stored = [_trim(s) for s in _all_samples()[:1]]
    loaded_at = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
    catalog = _catalog(
        stations=_all_samples(), cached={"loaded_at": loaded_at, "stations": stored}
    )

    result = await catalog.async_get_stations(WATER_LEVEL)

    catalog._client.async_get_stations.assert_awaited_once()
    assert fixtures.KAUB in {s.station_id for s in result}


@pytest.mark.asyncio
async def test_stale_list_is_kept_when_the_refresh_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test an outage does not empty the setup dialog once a list is cached."""
    stored = [_trim(s) for s in _all_samples()]
    loaded_at = (datetime.now(UTC) - timedelta(hours=30)).isoformat()
    catalog = _catalog(
        stations=PegelonlineConnectionError("down"),
        cached={"loaded_at": loaded_at, "stations": stored},
    )

    result = await catalog.async_get_stations(WATER_LEVEL)

    assert fixtures.KAUB in {s.station_id for s in result}
    assert "using the cached one" in caplog.text
    catalog._store.async_save.assert_not_awaited()


@pytest.mark.asyncio
async def test_failure_without_any_list_raises() -> None:
    """Test the first download failing is an error the config flow can report."""
    catalog = _catalog(stations=PegelonlineConnectionError("down"))

    with pytest.raises(PegelonlineConnectionError):
        await catalog.async_get_stations(WATER_LEVEL)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cached",
    [
        {"loaded_at": "garbage", "stations": []},
        {"stations": "garbage"},
        {},
    ],
)
async def test_damaged_stored_data_leads_to_a_download(cached: dict) -> None:
    """Test a corrupt store is treated as empty, not as a crash."""
    catalog = _catalog(stations=_all_samples(), cached=cached)

    result = await catalog.async_get_stations(WATER_LEVEL)

    assert fixtures.KAUB in {s.station_id for s in result}
    catalog._client.async_get_stations.assert_awaited_once()


@pytest.mark.asyncio
async def test_naive_stored_timestamp_is_read_as_utc() -> None:
    """Test a stored time without offset does not break the freshness check."""
    stored = [_trim(s) for s in _all_samples()]
    loaded_at = (datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    catalog = _catalog(cached={"loaded_at": loaded_at, "stations": stored})

    await catalog.async_get_stations(WATER_LEVEL)

    catalog._client.async_get_stations.assert_not_awaited()

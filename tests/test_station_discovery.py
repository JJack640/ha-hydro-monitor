"""Tests for the provider-independent station discovery."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hydro_monitor.core.station_discovery import (
    StationDiscoveryService,
)
from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers import PROVIDERS
from custom_components.hydro_monitor.providers.base import (
    ProviderDefinition,
    ProviderError,
)

LOCATION = "custom_components.hydro_monitor.core.station_discovery.async_get_home_location"


def _station(
    station_id: str,
    name: str,
    *,
    provider: str = "niwis",
    distance_km: float | None = None,
) -> HydroStation:
    """Create a minimal station fixture."""
    return HydroStation(
        provider=provider,
        station_id=station_id,
        name=name,
        measurement_types=(HydroMeasurementType.GROUNDWATER_LEVEL,),
        distance_km=distance_km,
    )


def _provider(
    provider_id: str,
    catalog: object,
    measurement_types: frozenset[HydroMeasurementType] = frozenset(
        HydroMeasurementType
    ),
) -> ProviderDefinition:
    """Create a provider definition around a fake catalog."""
    return ProviderDefinition(
        id=provider_id,
        name=provider_id.upper(),
        measurement_types=measurement_types,
        update_interval=timedelta(hours=1),
        observation_sensor_keys=None,
        create_catalog=MagicMock(return_value=catalog),
        get_station=AsyncMock(),
        create_fetcher=MagicMock(),
    )


def _catalog(result: object) -> MagicMock:
    """Create a fake catalog answering with a list or raising an error."""
    catalog = MagicMock()
    if isinstance(result, BaseException):
        catalog.async_nearby_stations = AsyncMock(side_effect=result)
    else:
        catalog.async_nearby_stations = AsyncMock(return_value=result)
    return catalog


@pytest.fixture
def location():
    """Patch the home location."""
    with patch(LOCATION) as patched:
        patched.return_value.latitude = 48.1
        patched.return_value.longitude = 11.5
        yield patched


def _registry(**catalogs: object):
    """Replace the provider registry with fake providers."""
    return patch.dict(
        PROVIDERS,
        {pid: _provider(pid, catalog) for pid, catalog in catalogs.items()},
        clear=True,
    )


@pytest.mark.asyncio
async def test_station_discovery(location) -> None:
    """Test discovery returns the stations of a single provider."""
    stations = [
        _station("S1", "Inkofen", distance_km=1.0),
        _station("S2", "Unering", distance_km=2.0),
    ]

    with _registry(niwis=_catalog(stations)):
        result = await StationDiscoveryService(AsyncMock()).async_discover(
            HydroMeasurementType.GROUNDWATER_LEVEL
        )

    assert result == stations


@pytest.mark.asyncio
async def test_discovery_merges_providers_by_distance(location) -> None:
    """Test stations of all providers come as one list, nearest first."""
    niwis = _catalog(
        [
            _station("N1", "Inkofen", distance_km=3.0),
            _station("N2", "Unering", distance_km=9.0),
        ]
    )
    other = _catalog(
        [
            _station("P1", "Pegel A", provider="other", distance_km=1.0),
            _station("P2", "Pegel B", provider="other", distance_km=5.0),
        ]
    )

    with _registry(niwis=niwis, other=other):
        result = await StationDiscoveryService(AsyncMock()).async_discover(
            HydroMeasurementType.GROUNDWATER_LEVEL, limit=3
        )

    assert [(s.provider, s.station_id) for s in result] == [
        ("other", "P1"),
        ("niwis", "N1"),
        ("other", "P2"),
    ]
    for catalog in (niwis, other):
        catalog.async_nearby_stations.assert_awaited_once_with(
            HydroMeasurementType.GROUNDWATER_LEVEL,
            latitude=48.1,
            longitude=11.5,
            limit=3,
        )


@pytest.mark.asyncio
async def test_station_in_two_providers_is_listed_twice(location) -> None:
    """Test a gauge known to both providers appears once per provider."""
    niwis = _catalog([_station("KAUB", "Kaub", distance_km=40.0)])
    other = _catalog([_station("uuid-1", "Kaub", provider="other", distance_km=40.0)])

    with _registry(niwis=niwis, other=other):
        result = await StationDiscoveryService(AsyncMock()).async_discover(
            HydroMeasurementType.GROUNDWATER_LEVEL
        )

    assert [s.provider for s in result] == ["niwis", "other"]


@pytest.mark.asyncio
async def test_one_failing_provider_does_not_empty_the_list(location) -> None:
    """Test the other providers still answer when one is down."""
    niwis = _catalog(ProviderError("down"))
    other = _catalog([_station("P1", "Pegel A", provider="other", distance_km=1.0)])

    with _registry(niwis=niwis, other=other):
        result = await StationDiscoveryService(AsyncMock()).async_discover(
            HydroMeasurementType.GROUNDWATER_LEVEL
        )

    assert [s.station_id for s in result] == ["P1"]


@pytest.mark.asyncio
async def test_all_providers_failing_raises(location) -> None:
    """Test the config flow can tell that nothing could be reached."""
    with _registry(
        niwis=_catalog(ProviderError("first")),
        other=_catalog(ProviderError("second")),
    ):
        with pytest.raises(ProviderError, match="first"):
            await StationDiscoveryService(AsyncMock()).async_discover(
                HydroMeasurementType.GROUNDWATER_LEVEL
            )


@pytest.mark.asyncio
async def test_unexpected_errors_are_not_swallowed(location) -> None:
    """Test a programming error in a catalog still surfaces."""
    with _registry(niwis=_catalog(KeyError("bug")), other=_catalog([])):
        with pytest.raises(KeyError):
            await StationDiscoveryService(AsyncMock()).async_discover(
                HydroMeasurementType.GROUNDWATER_LEVEL
            )


@pytest.mark.asyncio
async def test_provider_without_the_measurement_type_is_skipped(location) -> None:
    """Test only providers offering the measurement type are asked."""
    niwis = _catalog([_station("N1", "Inkofen", distance_km=1.0)])
    levels_only = _catalog([])

    with patch.dict(
        PROVIDERS,
        {
            "niwis": _provider("niwis", niwis),
            "levels_only": _provider(
                "levels_only", levels_only, frozenset({HydroMeasurementType.WATER_LEVEL})
            ),
        },
        clear=True,
    ):
        result = await StationDiscoveryService(AsyncMock()).async_discover(
            HydroMeasurementType.GROUNDWATER_LEVEL
        )

    assert [s.station_id for s in result] == ["N1"]
    levels_only.async_nearby_stations.assert_not_awaited()


@pytest.mark.asyncio
async def test_station_search(location) -> None:
    """Test that search filters by name case-insensitively, order kept."""
    catalog = _catalog(
        [
            _station("S1", "Inkofen"),
            _station("S2", "München-West"),
            _station("S3", "Unering"),
        ]
    )

    with _registry(niwis=catalog):
        result = await StationDiscoveryService(AsyncMock()).async_search(
            HydroMeasurementType.GROUNDWATER_LEVEL, "münchen"
        )

    assert [station.station_id for station in result] == ["S2"]
    catalog.async_nearby_stations.assert_awaited_once_with(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        latitude=48.1,
        longitude=11.5,
        limit=None,
    )


@pytest.mark.asyncio
async def test_station_search_spans_providers(location) -> None:
    """Test a search finds matches in every provider."""
    niwis = _catalog([_station("N1", "Kaub", distance_km=40.0)])
    other = _catalog(
        [
            _station("P1", "Kaub", provider="other", distance_km=40.0),
            _station("P2", "Worms", provider="other", distance_km=80.0),
        ]
    )

    with _registry(niwis=niwis, other=other):
        result = await StationDiscoveryService(AsyncMock()).async_search(
            HydroMeasurementType.GROUNDWATER_LEVEL, "kaub"
        )

    assert [(s.provider, s.station_id) for s in result] == [
        ("niwis", "N1"),
        ("other", "P1"),
    ]


@pytest.mark.asyncio
async def test_station_search_truncates_to_limit(location) -> None:
    """Test that search results are truncated to the requested limit."""
    catalog = _catalog([_station(f"S{i}", f"Quelle {i}") for i in range(5)])

    with _registry(niwis=catalog):
        result = await StationDiscoveryService(AsyncMock()).async_search(
            HydroMeasurementType.GROUNDWATER_LEVEL, "quelle", limit=2
        )

    assert len(result) == 2


@pytest.mark.asyncio
async def test_catalog_is_created_once_per_service(location) -> None:
    """Test a catalog (and its cache) lives as long as one config flow."""
    catalog = _catalog([_station("S1", "Quelle")])

    with _registry(niwis=catalog):
        service = StationDiscoveryService(AsyncMock())
        await service.async_discover(HydroMeasurementType.GROUNDWATER_LEVEL)
        await service.async_search(HydroMeasurementType.GROUNDWATER_LEVEL, "quelle")

        PROVIDERS["niwis"].create_catalog.assert_called_once()

"""Tests for the NIWIS station catalog."""

from unittest.mock import AsyncMock

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers.niwis.catalog import NiwisCatalog


def _station(station_id: str, *, latitude: float, longitude: float) -> HydroStation:
    """Create a minimal station fixture for distance-sorting tests."""
    return HydroStation(
        provider="niwis",
        station_id=station_id,
        name=station_id,
        measurement_types=(HydroMeasurementType.GROUNDWATER_LEVEL,),
        latitude=latitude,
        longitude=longitude,
    )


def _catalog(stations: list[HydroStation]) -> NiwisCatalog:
    """Build a catalog instance without running __init__."""
    catalog = NiwisCatalog.__new__(NiwisCatalog)
    catalog.async_get_stations = AsyncMock(return_value=stations)
    return catalog


@pytest.mark.asyncio
async def test_nearby_stations_returns_all_when_limit_is_none() -> None:
    """Test that limit=None returns every station, sorted by distance."""
    stations = [
        _station("far", latitude=52.5, longitude=13.4),  # Berlin-ish
        _station("near", latitude=48.11, longitude=11.6),  # right next door
        _station("mid", latitude=50.9, longitude=6.9),  # Cologne-ish
    ]
    catalog = _catalog(stations)

    result = await catalog.async_nearby_stations(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        latitude=48.1,
        longitude=11.5,
        limit=None,
    )

    assert [station.station_id for station in result] == ["near", "mid", "far"]


@pytest.mark.asyncio
async def test_nearby_stations_respects_limit() -> None:
    """Test that a limit truncates to just the nearest stations."""
    stations = [
        _station("far", latitude=52.5, longitude=13.4),
        _station("near", latitude=48.11, longitude=11.6),
        _station("mid", latitude=50.9, longitude=6.9),
    ]
    catalog = _catalog(stations)

    result = await catalog.async_nearby_stations(
        HydroMeasurementType.GROUNDWATER_LEVEL,
        latitude=48.1,
        longitude=11.5,
        limit=1,
    )

    assert [station.station_id for station in result] == ["near"]

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hydro_monitor.core.station_discovery import (
    StationDiscoveryService,
)
from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation


@pytest.mark.asyncio
async def test_station_discovery():
    hass = AsyncMock()

    with (
        patch(
            "custom_components.hydro_monitor.core.station_discovery.async_get_home_location"
        ) as location,
        patch(
            "custom_components.hydro_monitor.core.station_discovery.NiwisCatalog"
        ) as catalog,
    ):
        location.return_value.latitude = 48.1
        location.return_value.longitude = 11.5

        catalog.return_value.async_nearby_stations = AsyncMock(
            return_value=["station1", "station2"]
        )

        discovery = StationDiscoveryService(hass)

        result = await discovery.async_discover(HydroMeasurementType.GROUNDWATER_LEVEL)

        assert result == ["station1", "station2"]


def _station(station_id: str, name: str) -> HydroStation:
    """Create a minimal station fixture for search tests."""
    return HydroStation(
        provider="niwis",
        station_id=station_id,
        name=name,
        measurement_types=(HydroMeasurementType.GROUNDWATER_LEVEL,),
    )


@pytest.mark.asyncio
async def test_station_search():
    """Test that search filters by name case-insensitively, sorted results kept."""
    hass = AsyncMock()

    with (
        patch(
            "custom_components.hydro_monitor.core.station_discovery.async_get_home_location"
        ) as location,
        patch(
            "custom_components.hydro_monitor.core.station_discovery.NiwisCatalog"
        ) as catalog,
    ):
        location.return_value.latitude = 48.1
        location.return_value.longitude = 11.5

        nearby_stations = AsyncMock(
            return_value=[
                _station("S1", "Inkofen"),
                _station("S2", "München-West"),
                _station("S3", "Unering"),
            ]
        )
        catalog.return_value.async_nearby_stations = nearby_stations

        discovery = StationDiscoveryService(hass)

        result = await discovery.async_search(
            HydroMeasurementType.GROUNDWATER_LEVEL, "münchen"
        )

        assert [station.station_id for station in result] == ["S2"]
        nearby_stations.assert_awaited_once_with(
            HydroMeasurementType.GROUNDWATER_LEVEL,
            latitude=48.1,
            longitude=11.5,
            limit=None,
        )


@pytest.mark.asyncio
async def test_station_search_truncates_to_limit():
    """Test that search results are truncated to the requested limit."""
    hass = AsyncMock()

    with (
        patch(
            "custom_components.hydro_monitor.core.station_discovery.async_get_home_location"
        ) as location,
        patch(
            "custom_components.hydro_monitor.core.station_discovery.NiwisCatalog"
        ) as catalog,
    ):
        location.return_value.latitude = 48.1
        location.return_value.longitude = 11.5

        catalog.return_value.async_nearby_stations = AsyncMock(
            return_value=[_station(f"S{i}", f"Quelle {i}") for i in range(5)]
        )

        discovery = StationDiscoveryService(hass)

        result = await discovery.async_search(
            HydroMeasurementType.GROUNDWATER_LEVEL, "quelle", limit=2
        )

        assert len(result) == 2

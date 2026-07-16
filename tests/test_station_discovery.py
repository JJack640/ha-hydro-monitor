from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hydro_monitor.core.station_discovery import (
    StationDiscoveryService,
)
from custom_components.hydro_monitor.models import HydroMeasurementType


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

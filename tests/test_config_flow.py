"""Tests for the Hydro Monitor config flow."""

from unittest.mock import AsyncMock

import pytest

from custom_components.hydro_monitor.config_flow import HydroMonitorConfigFlow
from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation


@pytest.mark.asyncio
async def test_station_step_routes_search_sentinel_to_search_step() -> None:
    """Test that picking the search entry routes to async_step_search.

    A missing or misordered sentinel check would instead cause a KeyError
    when looking the sentinel value up in self._stations.
    """
    flow = HydroMonitorConfigFlow()
    flow._measurement_type = HydroMeasurementType.GROUNDWATER_LEVEL
    flow._stations = {
        "S1": HydroStation(
            provider="niwis",
            station_id="S1",
            name="Test Station",
            measurement_types=(HydroMeasurementType.GROUNDWATER_LEVEL,),
        )
    }
    flow.async_step_search = AsyncMock(return_value="search_step_result")

    result = await flow.async_step_station(user_input={"station_id": "__search__"})

    assert result == "search_step_result"
    flow.async_step_search.assert_awaited_once()

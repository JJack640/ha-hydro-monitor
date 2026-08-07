"""Tests for the Hydro Monitor config flow."""

from unittest.mock import AsyncMock, MagicMock

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


@pytest.mark.parametrize(
    ("configured_language", "expected_name"),
    [
        ("de", "Abfluss"),
        ("de-DE", "Abfluss"),
        ("en", "Discharge"),
        (None, "Discharge"),
    ],
)
def test_measurement_type_display_name_follows_hass_language(
    configured_language: str | None, expected_name: str
) -> None:
    """Test that the config entry title's measurement type follows hass.config.language.

    Config entry titles, like device model text, have no translation_key
    mechanism -- an unlocalized title was the reported bug this guards
    against (English title shown on an otherwise German-configured
    instance).
    """
    flow = HydroMonitorConfigFlow()
    flow._measurement_type = HydroMeasurementType.DISCHARGE
    flow.hass = MagicMock()
    flow.hass.config.language = configured_language

    assert flow._measurement_type_display_name() == expected_name


def test_measurement_type_display_name_empty_without_measurement_type() -> None:
    """Test the empty-string fallback before a measurement type is chosen."""
    flow = HydroMonitorConfigFlow()
    flow._measurement_type = None
    flow.hass = MagicMock()
    flow.hass.config.language = "de"

    assert flow._measurement_type_display_name() == ""

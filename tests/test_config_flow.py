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


def _flow_station(provider: str, station_id: str, name: str) -> HydroStation:
    return HydroStation(
        provider=provider,
        station_id=station_id,
        name=name,
        measurement_types=(HydroMeasurementType.WATER_LEVEL,),
        waterbody="RHEIN",
        distance_km=12.34,
    )


def test_station_label_names_the_source() -> None:
    """Test the combined list tells which provider a station comes from."""
    from custom_components.hydro_monitor.config_flow import _station_label

    label = _station_label(_flow_station("niwis", "S1", "Kaub"))

    assert label == "Kaub · RHEIN · 12.3 km · NIWIS"


def test_station_label_falls_back_to_the_provider_id() -> None:
    """Test a provider missing from the registry still gets a label."""
    from custom_components.hydro_monitor.config_flow import _station_label

    label = _station_label(_flow_station("gone", "S1", "Kaub"))

    assert label.endswith(" · gone")


def test_station_key_differs_between_providers() -> None:
    """Test the same id from two providers cannot clash in the dropdown."""
    from custom_components.hydro_monitor.config_flow import _station_key

    assert _station_key(_flow_station("niwis", "X", "A")) != _station_key(
        _flow_station("other", "X", "A")
    )


@pytest.mark.asyncio
async def test_entry_uses_the_selected_stations_provider() -> None:
    """Test unique id and data follow the station's provider, not a constant."""
    flow = HydroMonitorConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config.language = "en"
    flow._measurement_type = HydroMeasurementType.WATER_LEVEL
    flow._stations = {"other:abc": _flow_station("other", "abc", "Kaub")}
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value="created")

    await flow.async_step_station(user_input={"station_id": "other:abc"})

    flow.async_set_unique_id.assert_awaited_once_with("other:abc:water_level")
    assert flow.async_create_entry.call_args.kwargs["data"]["provider"] == "other"


@pytest.mark.asyncio
async def test_provider_failure_aborts_with_cannot_connect() -> None:
    """Test any provider error (not just NIWIS) aborts the flow."""
    from custom_components.hydro_monitor.providers.base import ProviderError

    flow = HydroMonitorConfigFlow()
    flow._measurement_type = HydroMeasurementType.WATER_LEVEL
    discovery = MagicMock()
    discovery.async_discover = AsyncMock(side_effect=ProviderError("down"))
    flow._discovery = discovery
    flow.async_abort = MagicMock(return_value="aborted")

    result = await flow.async_step_station()

    assert result == "aborted"
    flow.async_abort.assert_called_once_with(reason="cannot_connect")

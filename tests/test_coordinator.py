"""Tests for the Hydro Monitor coordinator."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers.niwis.api import NiwisConnectionError
from custom_components.hydro_monitor.providers.niwis.const import (
    DERIVED_ENDPOINT_LOW_WATER_CLASS,
)


def _station() -> HydroStation:
    """Create a representative station for coordinator tests."""
    return HydroStation(
        provider="niwis",
        station_id="DESM_DEBY16607001",
        name="Inkofen",
        measurement_types=(HydroMeasurementType.DISCHARGE,),
    )


def _series() -> list[dict[str, object]]:
    """Create a minimal single-point NIWIS series."""
    return [{"datum": "2026-07-20", "messwert": "10,5", "einheit": "m³/s", "flag": "A"}]


def _classification_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS classification response."""
    response: dict[str, object] = {
        "einzelwert": "extrem niedrig",
        "einheit": None,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _coordinator(client: AsyncMock) -> HydroMonitorCoordinator:
    """Build a coordinator instance without running __init__."""
    coordinator = HydroMonitorCoordinator.__new__(HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.client = client
    return coordinator


@pytest.mark.asyncio
async def test_update_merges_low_water_class_on_success() -> None:
    """Test that a successful classification call is merged into the observation."""
    client = AsyncMock()
    client.async_get_series.return_value = _series()
    client.async_get_derived_result.return_value = _classification_response()

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.low_water_class == "extrem niedrig"
    assert observation.low_water_class_error is None


@pytest.mark.asyncio
async def test_update_raises_update_failed_on_primary_series_failure() -> None:
    """Test that a failed primary series fetch fails the whole update."""
    client = AsyncMock()
    client.async_get_series.side_effect = NiwisConnectionError("boom")

    with pytest.raises(UpdateFailed):
        await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_not_called()


@pytest.mark.asyncio
async def test_update_survives_classification_failure() -> None:
    """Test that a failed classification call does not fail the whole update."""
    client = AsyncMock()
    client.async_get_series.return_value = _series()
    client.async_get_derived_result.side_effect = NiwisConnectionError(
        "classification down"
    )

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.low_water_class is None
    assert observation.low_water_class_error == "classification down"


@pytest.mark.asyncio
async def test_update_requests_expected_classification_parameters() -> None:
    """Test the exact endpoint and params sent for the classification request."""
    client = AsyncMock()
    client.async_get_series.return_value = _series()
    client.async_get_derived_result.return_value = _classification_response()

    await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_awaited_once_with(
        DERIVED_ENDPOINT_LOW_WATER_CLASS,
        {
            "abgeleiteteGroesse": "Abfluss Niedrigwasserklasse aktueller Tag",
            "messstelleNr": "DESM_DEBY16607001",
            "jahresdefinition": "KALENDERJAHR",
            "startJahr": "1991",
            "endJahr": "2020",
        },
    )

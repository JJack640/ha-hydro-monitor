"""Tests for the provider-independent Hydro Monitor coordinator."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import (
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from custom_components.hydro_monitor.providers import PROVIDERS
from custom_components.hydro_monitor.providers.base import (
    ProviderDefinition,
    ProviderError,
)


def _station(provider: str = "niwis") -> HydroStation:
    return HydroStation(
        provider=provider,
        station_id="DESM_DEBY16607001",
        name="Inkofen",
        measurement_types=(HydroMeasurementType.DISCHARGE,),
    )


def _observation() -> HydroObservation:
    return HydroObservation(
        HydroMeasurementType.DISCHARGE, 10.5, "m³/s", date(2026, 7, 20)
    )


def _coordinator(fetcher: AsyncMock) -> HydroMonitorCoordinator:
    """Build a coordinator around a fetcher without running __init__."""
    coordinator = HydroMonitorCoordinator.__new__(HydroMonitorCoordinator)
    coordinator.fetcher = fetcher
    return coordinator


@pytest.mark.asyncio
async def test_update_returns_the_fetchers_observation() -> None:
    """Test the coordinator hands out whatever the provider's fetcher builds."""
    fetcher = AsyncMock()
    fetcher.async_update.return_value = _observation()

    assert await _coordinator(fetcher)._async_update_data() == _observation()


@pytest.mark.asyncio
async def test_provider_error_becomes_update_failed() -> None:
    """Test any provider's failure fails the update with its message."""
    fetcher = AsyncMock()
    fetcher.async_update.side_effect = ProviderError("boom")

    with pytest.raises(UpdateFailed, match="boom"):
        await _coordinator(fetcher)._async_update_data()


@pytest.mark.asyncio
async def test_programming_errors_are_not_hidden_as_update_failed() -> None:
    """Test a bug in a fetcher is not mistaken for a provider outage."""
    fetcher = AsyncMock()
    fetcher.async_update.side_effect = KeyError("bug")

    with pytest.raises(KeyError):
        await _coordinator(fetcher)._async_update_data()


def test_init_takes_fetcher_and_interval_from_the_stations_provider() -> None:
    """Test the coordinator is configured by the provider of its station."""
    fetcher = MagicMock()
    provider = ProviderDefinition(
        id="other",
        name="Other",
        measurement_types=frozenset(HydroMeasurementType),
        update_interval=timedelta(minutes=30),
        observation_sensor_keys=None,
        create_catalog=MagicMock(),
        get_station=AsyncMock(),
        create_fetcher=MagicMock(return_value=fetcher),
    )
    hass = MagicMock()
    entry = MagicMock()
    station = _station("other")

    with (
        patch.dict(PROVIDERS, {"other": provider}),
        patch.object(DataUpdateCoordinator, "__init__", return_value=None) as init,
    ):
        coordinator = HydroMonitorCoordinator(
            hass, entry, station, HydroMeasurementType.DISCHARGE
        )

    provider.create_fetcher.assert_called_once_with(
        hass, station, HydroMeasurementType.DISCHARGE
    )
    assert coordinator.fetcher is fetcher
    assert coordinator.station is station
    assert init.call_args.kwargs["update_interval"] == timedelta(minutes=30)
    assert init.call_args.kwargs["name"] == "hydro_monitor_DESM_DEBY16607001_discharge"
    assert init.call_args.kwargs["config_entry"] is entry

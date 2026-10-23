"""Tests for which sensors a config entry gets."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import (
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from custom_components.hydro_monitor.providers import PROVIDERS
from custom_components.hydro_monitor.providers.base import ProviderDefinition
from custom_components.hydro_monitor.sensor import (
    SENSOR_DESCRIPTIONS,
    HydroObservationSensor,
    async_setup_entry,
)


def _entry(provider: str) -> SimpleNamespace:
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = HydroStation(
        provider=provider,
        station_id="S1",
        name="Station",
        measurement_types=(HydroMeasurementType.WATER_LEVEL,),
    )
    coordinator.measurement_type = HydroMeasurementType.WATER_LEVEL
    coordinator.data = HydroObservation(
        HydroMeasurementType.WATER_LEVEL, 40.0, "cm", date(2026, 10, 23)
    )
    coordinator.last_update_success = True
    return SimpleNamespace(runtime_data=SimpleNamespace(coordinator=coordinator))


def _provider(provider_id: str, keys: frozenset[str] | None) -> ProviderDefinition:
    return ProviderDefinition(
        id=provider_id,
        name=provider_id,
        measurement_types=frozenset(HydroMeasurementType),
        update_interval=timedelta(hours=1),
        observation_sensor_keys=keys,
        create_catalog=MagicMock(),
        get_station=AsyncMock(),
        create_fetcher=MagicMock(),
    )


async def _created_observation_keys(entry: SimpleNamespace) -> list[str]:
    add_entities = MagicMock()

    await async_setup_entry(MagicMock(), entry, add_entities)

    (entities,) = add_entities.call_args.args
    return [
        entity.entity_description.key
        for entity in entities
        if isinstance(entity, HydroObservationSensor)
    ]


@pytest.mark.asyncio
async def test_niwis_entry_gets_every_observation_sensor() -> None:
    """Test NIWIS (no key list) keeps every sensor it always had.

    The 50 sensors NIWIS entries had before a second provider existed must
    not change; sensors only another provider can fill are not added.
    """
    keys = await _created_observation_keys(_entry("niwis"))

    assert keys == [
        description.key
        for description in SENSOR_DESCRIPTIONS
        if description.providers is None
    ]
    assert len(keys) == 50
    assert "level_state" not in keys


@pytest.mark.asyncio
async def test_provider_with_a_key_list_only_gets_those_sensors() -> None:
    """Test a provider that cannot fill every sensor creates only its own."""
    limited = _provider("limited", frozenset({"value", "change_1d", "trend_state"}))

    with patch.dict(PROVIDERS, {"limited": limited}):
        keys = await _created_observation_keys(_entry("limited"))

    assert keys == ["value", "change_1d", "trend_state"]


@pytest.mark.asyncio
async def test_sensor_order_follows_the_description_order() -> None:
    """Test filtering keeps the order of SENSOR_DESCRIPTIONS."""
    limited = _provider("limited", frozenset({"trend_state", "value"}))

    with patch.dict(PROVIDERS, {"limited": limited}):
        keys = await _created_observation_keys(_entry("limited"))

    assert keys == ["value", "trend_state"]


@pytest.mark.asyncio
async def test_provider_only_sensor_needs_its_provider() -> None:
    """Test a provider-restricted sensor is created for that provider alone.

    A provider that lists no keys (all of them) still must not get a sensor
    that only another provider can ever fill.
    """
    everything = _provider("other", None)
    pegelonline = _provider("pegelonline", None)

    with patch.dict(PROVIDERS, {"other": everything, "pegelonline": pegelonline}):
        other_keys = await _created_observation_keys(_entry("other"))
        pegelonline_keys = await _created_observation_keys(_entry("pegelonline"))

    assert "level_state" not in other_keys
    assert "level_state" in pegelonline_keys

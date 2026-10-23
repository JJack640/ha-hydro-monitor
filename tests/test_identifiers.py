"""Regression guards for the identifiers existing NIWIS users depend on.

Config entries, devices and entities are matched by these exact strings.
Changing any of them would orphan existing entities and lose their history,
so the multi-provider refactor must keep them byte-for-byte.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hydro_monitor.config_flow import HydroMonitorConfigFlow
from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import (
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from custom_components.hydro_monitor.sensor import (
    SENSOR_DESCRIPTIONS,
    STATION_SENSOR_DESCRIPTIONS,
    HydroObservationSensor,
    HydroStationSensor,
)


def _station() -> HydroStation:
    return HydroStation(
        provider="niwis",
        station_id="DESM_DEBY16607001",
        name="Inkofen",
        measurement_types=(HydroMeasurementType.DISCHARGE,),
        station_type="Pegel",
    )


def _coordinator() -> MagicMock:
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        HydroMeasurementType.DISCHARGE, 10.5, "m³/s", date(2026, 7, 20)
    )
    coordinator.last_update_success = True
    return coordinator


def _description(key: str):
    return next(d for d in SENSOR_DESCRIPTIONS if d.key == key)


def test_observation_entity_unique_id_is_unchanged() -> None:
    """Test `{provider}_{station_id}_{measurement_type}_{key}`."""
    sensor = HydroObservationSensor(_coordinator(), _description("value"))

    assert sensor.unique_id == "niwis_DESM_DEBY16607001_discharge_value"


def test_every_observation_entity_unique_id_keeps_the_pattern() -> None:
    """Test all 50 observation sensors, not just the primary one."""
    coordinator = _coordinator()

    for description in SENSOR_DESCRIPTIONS:
        sensor = HydroObservationSensor(coordinator, description)

        assert sensor.unique_id == f"niwis_DESM_DEBY16607001_discharge_{description.key}"


def test_station_entity_unique_id_is_unchanged() -> None:
    """Test `{provider}_{station_id}_{measurement_type}_station_{key}`."""
    description = next(d for d in STATION_SENSOR_DESCRIPTIONS if d.key == "station_type")

    sensor = HydroStationSensor(_coordinator(), description)

    assert sensor.unique_id == (
        "niwis_DESM_DEBY16607001_discharge_station_station_type"
    )


def test_device_identifier_is_unchanged() -> None:
    """Test `(hydro_monitor, {provider}:{station_id}:{measurement_type})`."""
    sensor = HydroObservationSensor(_coordinator(), _description("value"))

    assert sensor.device_info["identifiers"] == {
        ("hydro_monitor", "niwis:DESM_DEBY16607001:discharge")
    }


@pytest.mark.asyncio
async def test_config_entry_unique_id_and_data_are_unchanged() -> None:
    """Test selecting a NIWIS station yields the same entry as before."""
    flow = HydroMonitorConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config.language = "en"
    flow._measurement_type = HydroMeasurementType.DISCHARGE
    flow._stations = {"niwis:DESM_DEBY16607001": _station()}
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_create_entry = MagicMock(return_value="created")

    result = await flow.async_step_station(
        user_input={"station_id": "niwis:DESM_DEBY16607001"}
    )

    assert result == "created"
    flow.async_set_unique_id.assert_awaited_once_with(
        "niwis:DESM_DEBY16607001:discharge"
    )
    assert flow.async_create_entry.call_args.kwargs["data"] == {
        "provider": "niwis",
        "station_id": "DESM_DEBY16607001",
        "measurement_type": "discharge",
    }
    assert flow.async_create_entry.call_args.kwargs["title"] == "Inkofen – Discharge"

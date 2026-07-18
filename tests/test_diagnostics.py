"""Tests for Hydro Monitor diagnostics."""

from datetime import date
from types import SimpleNamespace

import pytest

from custom_components.hydro_monitor.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.hydro_monitor.models import (
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)


@pytest.mark.asyncio
async def test_config_entry_diagnostics():
    """Test diagnostics output."""

    station = HydroStation(
        provider="niwis",
        station_id="DEGM_TEST",
        name="Test Station",
        measurement_types=(HydroMeasurementType.GROUNDWATER_LEVEL,),
        latitude=48.1,
        longitude=11.6,
        waterbody="Groundwater",
        operator="LfU",
        institution="NIWIS",
        source_url="https://example.org",
        license_name="dl-de/by-2-0",
        distance_km=1.2,
    )

    observation = HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        observed_on=date(2026, 7, 15),
        quality_flag="A",
        change_1d=0.0,
        change_7d=-0.03,
        minimum_30d=608.07,
        maximum_30d=608.18,
        sample_count=29,
    )

    coordinator = SimpleNamespace(
        data=observation,
        station=station,
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        last_update_success=True,
        last_exception=None,
        update_interval=None,
    )

    runtime_data = SimpleNamespace(
        station=station,
        coordinator=coordinator,
    )

    entry = SimpleNamespace(
        title="Test",
        runtime_data=runtime_data,
    )

    diagnostics = await async_get_config_entry_diagnostics(
        None,
        entry,
    )

    assert diagnostics["config_entry"]["provider"] == "niwis"
    assert diagnostics["station"]["name"] == "Test Station"

    assert diagnostics["observation"]["value"] == 608.07
    assert diagnostics["observation"]["change_7d"] == -0.03
    assert diagnostics["observation"]["native_unit"] == "m. ü. NHN"
    assert diagnostics["observation"]["trend_state"] == "strong_falling"
    assert diagnostics["observation"]["is_stale"] is True

    # Privacy checks
    assert "latitude" not in diagnostics["station"]
    assert "longitude" not in diagnostics["station"]
    assert "distance_km" not in diagnostics["station"]

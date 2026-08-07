"""Tests for Hydro Monitor diagnostics."""

from datetime import date
from types import SimpleNamespace

import pytest

from custom_components.hydro_monitor.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.hydro_monitor.models import (
    HydroDerivedValue,
    HydroLowWaterBoundaries,
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
        low_water_class="extremely_low",
        low_water_class_raw="extrem niedrig",
        low_water_class_error=None,
        official_development_7d="gleichbleibend",
        official_development_7d_raw="gleichbleibend",
        official_development_7d_error=None,
        boundaries=HydroLowWaterBoundaries(
            classification_labels=("extremely_low", "very_low", "low", "no_low_water"),
            open_ended=True,
            static_thresholds=(20.3, 25.0, 33.4),
            static_unit="m³/s",
            static_error=None,
            dynamic_thresholds=(24.3, 26.0, 33.6),
            dynamic_unit="m³/s",
            dynamic_reference_date=date(2026, 7, 15),
            dynamic_error=None,
        ),
        mq=HydroDerivedValue(value=46.41388, unit="m³/s", error=None),
        mnq=HydroDerivedValue(value=25.013334, unit="m³/s", error=None),
        nm7q=HydroDerivedValue(value=15.257143, unit="m³/s", error=None),
        nm30q=HydroDerivedValue(value=17.503448, unit="m³/s", error=None),
        mw=HydroDerivedValue(value=88.48911, unit="cm", error=None),
        mnw=HydroDerivedValue(value=49.866665, unit="cm", error=None),
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
    assert diagnostics["observation"]["low_water_class"] == "extremely_low"
    assert diagnostics["observation"]["low_water_class_raw"] == "extrem niedrig"
    assert diagnostics["observation"]["low_water_class_error"] is None
    assert diagnostics["observation"]["official_development_7d"] == "gleichbleibend"
    assert diagnostics["observation"]["official_development_7d_raw"] == "gleichbleibend"
    assert diagnostics["observation"]["official_development_7d_error"] is None

    boundaries = diagnostics["observation"]["boundaries"]
    assert boundaries["classification_labels"] == [
        "extremely_low",
        "very_low",
        "low",
        "no_low_water",
    ]
    assert boundaries["open_ended"] is True
    assert boundaries["static_thresholds"] == [20.3, 25.0, 33.4]
    assert boundaries["static_unit"] == "m³/s"
    assert boundaries["static_error"] is None
    assert boundaries["dynamic_thresholds"] == [24.3, 26.0, 33.6]
    assert boundaries["dynamic_unit"] == "m³/s"
    assert boundaries["dynamic_reference_date"] == "2026-07-15"
    assert boundaries["dynamic_error"] is None

    historical_statistics = diagnostics["observation"]["historical_statistics"]
    assert historical_statistics["mq"] == {
        "value": pytest.approx(46.41388),
        "unit": "m³/s",
        "error": None,
    }
    assert historical_statistics["mnq"] == {
        "value": pytest.approx(25.013334),
        "unit": "m³/s",
        "error": None,
    }
    assert historical_statistics["nm7q"] == {
        "value": pytest.approx(15.257143),
        "unit": "m³/s",
        "error": None,
    }
    assert historical_statistics["nm30q"] == {
        "value": pytest.approx(17.503448),
        "unit": "m³/s",
        "error": None,
    }
    assert historical_statistics["mw"] == {
        "value": pytest.approx(88.48911),
        "unit": "cm",
        "error": None,
    }
    assert historical_statistics["mnw"] == {
        "value": pytest.approx(49.866665),
        "unit": "cm",
        "error": None,
    }

    # Station metadata
    assert diagnostics["station"]["latitude"] == 48.1
    assert diagnostics["station"]["longitude"] == 11.6
    assert diagnostics["station"]["distance_km"] == 1.2
    assert diagnostics["station"]["waterbody"] == "Groundwater"
    assert diagnostics["station"]["operator"] == "LfU"
    assert diagnostics["station"]["institution"] == "NIWIS"
    assert diagnostics["station"]["license"] == "dl-de/by-2-0"
    assert diagnostics["station"]["country_code"] is None
    assert diagnostics["station"]["station_type"] is None
    assert diagnostics["station"]["locality"] is None

    assert diagnostics["station"]["waterbody_code"] is None
    assert diagnostics["station"]["waterbody_position"] is None
    assert diagnostics["station"]["catchment_area_km2"] is None

    assert diagnostics["station"]["elevation_ground"] is None
    assert diagnostics["station"]["gauge_zero_elevation"] is None
    assert diagnostics["station"]["elevation_system"] is None

    assert diagnostics["station"]["hydrogeological_region"] is None
    assert diagnostics["station"]["hydrogeological_region_code"] is None

    assert diagnostics["station"]["operator_url"] is None
    assert diagnostics["station"]["institution_url"] is None

    assert diagnostics["station"]["remarks"] is None
    assert diagnostics["station"]["historical_low_discharge"] is None
    assert diagnostics["station"]["historical_low_discharge_date"] is None
    assert diagnostics["station"]["historical_low_water_level"] is None
    assert diagnostics["station"]["historical_low_water_level_date"] is None

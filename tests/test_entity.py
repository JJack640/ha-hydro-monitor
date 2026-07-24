"""Tests for Hydro Monitor entities."""

from datetime import date
from unittest.mock import MagicMock

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import (
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from custom_components.hydro_monitor.sensor import (
    SENSOR_DESCRIPTIONS,
    HydroObservationSensor,
)


def _observation() -> HydroObservation:
    """Create a representative observation."""
    return HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        observed_on=date(2026, 7, 15),
        quality_flag="A",
        sample_count=29,
    )


def _station() -> HydroStation:
    """Create a representative station."""
    return HydroStation(
        provider="niwis",
        station_id="DEGM_DEBY83614",
        name="NBS-H/W KB 11/1",
        measurement_types=(HydroMeasurementType.GROUNDWATER_LEVEL,),
        latitude=50.203686,
        longitude=9.621822,
        country_code="DEBY",
        locality="Obersinn",
        waterbody=None,
        waterbody_code=None,
        waterbody_position=None,
        catchment_area_km2=None,
        elevation_ground=233.3,
        gauge_zero_elevation=None,
        elevation_system="DHHN12",
        hydrogeological_region="Spessart",
        hydrogeological_region_code="6201",
        station_type="W",
        operator="WWA AB",
        institution="LFU BY",
        license_name="cc-by/4.0",
        source_url="https://example.org",
        remarks="Test station",
        historical_low_discharge=None,
        historical_low_discharge_date=None,
        historical_low_water_level=None,
        historical_low_water_level_date=None,
    )


def test_primary_sensor_extra_state_attributes() -> None:
    """Test primary sensor exposes station metadata."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.GROUNDWATER_LEVEL
    coordinator.data = _observation()
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=SENSOR_DESCRIPTIONS[0],
    )

    attributes = sensor.extra_state_attributes

    assert attributes["provider"] == "niwis"
    assert attributes["station_id"] == "DEGM_DEBY83614"
    assert attributes["quality_flag"] == "A"
    assert attributes["sample_count"] == 29
    assert attributes["observed_on"] == "2026-07-15"

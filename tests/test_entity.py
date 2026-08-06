"""Tests for Hydro Monitor entities."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import (
    HydroLowWaterBoundaries,
    HydroMeasurementType,
    HydroObservation,
    HydroStation,
)
from custom_components.hydro_monitor.sensor import (
    SENSOR_DESCRIPTIONS,
    HydroObservationSensor,
)


def _description(key: str):
    """Return one sensor description by key."""
    return next(
        description for description in SENSOR_DESCRIPTIONS if description.key == key
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


def test_low_water_class_sensor_exposes_official_error_message() -> None:
    """Test that the low-water class sensor surfaces NIWIS's error message."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.GROUNDWATER_LEVEL
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        observed_on=date(2026, 7, 15),
        low_water_class=None,
        low_water_class_raw=None,
        low_water_class_error="Zu viele Fehlwerte im Referenzzeitraum",
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("low_water_class"),
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {
        "raw_value": None,
        "error": "Zu viele Fehlwerte im Referenzzeitraum",
    }


def test_low_water_class_sensor_exposes_raw_value_for_unmapped_label() -> None:
    """Test that an unrecognized NIWIS label is surfaced via raw_value."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.GROUNDWATER_LEVEL
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        observed_on=date(2026, 7, 15),
        low_water_class=None,
        low_water_class_raw="irgendwas",
        low_water_class_error=None,
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("low_water_class"),
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {
        "raw_value": "irgendwas",
        "error": None,
    }


def test_static_boundary_sensor_exposes_error() -> None:
    """Test that a static-boundary sensor surfaces its own error, not the 366-row array."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.GROUNDWATER_LEVEL
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        observed_on=date(2026, 7, 15),
        boundaries=HydroLowWaterBoundaries(static_error="static down"),
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("boundary_static_extremely_low"),
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {"error": "static down"}


def test_dynamic_boundary_sensor_exposes_error_and_reference_date() -> None:
    """Test that a dynamic-boundary sensor surfaces its error and reference date."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.GROUNDWATER_LEVEL
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        observed_on=date(2026, 7, 15),
        boundaries=HydroLowWaterBoundaries(
            dynamic_thresholds=(24.3, 26.0, 33.6),
            dynamic_unit="m³/s",
            dynamic_reference_date=date(2026, 7, 15),
        ),
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("boundary_dynamic_extremely_low"),
    )

    assert sensor.native_value == pytest.approx(24.3)
    assert sensor.extra_state_attributes == {
        "error": None,
        "reference_date": "2026-07-15",
    }

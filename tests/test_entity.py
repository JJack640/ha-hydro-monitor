"""Tests for Hydro Monitor entities."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import (
    HydroDeciles,
    HydroDerivedValue,
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


def test_official_development_7d_sensor_exposes_official_error_message() -> None:
    """Test that the development-7d sensor surfaces NIWIS's error message."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
        official_development_7d=None,
        official_development_7d_raw=None,
        official_development_7d_error="Zu viele Fehlwerte im Referenzzeitraum",
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("official_development_7d"),
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {
        "raw_value": None,
        "error": "Zu viele Fehlwerte im Referenzzeitraum",
    }


def test_official_development_7d_sensor_becomes_unavailable_when_not_supported() -> None:
    """Test that the sensor auto-hides for measurement types without this quantity.

    Groundwater/spring-discharge coordinators never fetch this quantity, so
    the model field stays at its None default and the entity should behave
    exactly as if the fetch had failed: unavailable, not an error state.
    """
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.GROUNDWATER_LEVEL
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.GROUNDWATER_LEVEL,
        value=608.07,
        unit="m. ü. NHN",
        observed_on=date(2026, 7, 15),
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("official_development_7d"),
    )

    assert sensor.native_value is None
    assert sensor.available is False


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


def test_decile_sensor_exposes_error_and_reference_date() -> None:
    """Test that a decile sensor surfaces its error and reference date."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
        deciles=HydroDeciles(
            thresholds=(
                10.0,
                12.0,
                14.0,
                16.0,
                18.0,
                20.0,
                22.0,
                24.0,
                26.0,
                28.0,
                30.0,
            ),
            unit="m³/s",
            reference_date=date(2026, 7, 15),
        ),
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("decile_p50"),
    )

    assert sensor.native_value == pytest.approx(20.0)
    assert sensor.extra_state_attributes == {
        "error": None,
        "reference_date": "2026-07-15",
    }


@pytest.mark.parametrize("key", ["mq", "mnq", "nm7q", "nm30q", "mw", "mnw"])
def test_historical_statistic_sensor_exposes_error(key: str) -> None:
    """Test that a historical-statistic sensor surfaces its own error."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
        **{key: HydroDerivedValue(error="mq down")},
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description(key),
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {"error": "mq down"}


@pytest.mark.parametrize("key", ["mq", "mnq", "nm7q", "nm30q", "mw", "mnw"])
def test_historical_statistic_sensor_reports_value(key: str) -> None:
    """Test that a historical-statistic sensor reports its numeric value."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
        **{key: HydroDerivedValue(value=46.41388, unit="m³/s", error=None)},
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description(key),
    )

    assert sensor.native_value == pytest.approx(46.41388)
    assert sensor.extra_state_attributes == {"error": None}


@pytest.mark.parametrize(
    ("key", "stat_key"),
    [
        ("percent_of_mq", "mq"),
        ("percent_of_mnq", "mnq"),
        ("percent_of_mw", "mw"),
        ("percent_of_mnw", "mnw"),
    ],
)
def test_percent_of_statistic_sensor_exposes_error(key: str, stat_key: str) -> None:
    """Test that a %-of-statistic sensor surfaces the underlying statistic's error."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
        **{stat_key: HydroDerivedValue(error="stat down")},
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description(key),
    )

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {"error": "stat down"}


@pytest.mark.parametrize(
    ("measurement_type", "expected_name"),
    [
        (HydroMeasurementType.DISCHARGE, "Discharge"),
        (HydroMeasurementType.WATER_LEVEL, "Water level"),
        (HydroMeasurementType.GROUNDWATER_LEVEL, "Groundwater level"),
        (HydroMeasurementType.SPRING_DISCHARGE, "Spring discharge"),
    ],
)
def test_device_model_includes_measurement_type(
    measurement_type: HydroMeasurementType, expected_name: str
) -> None:
    """Test that the device model distinguishes same-station, different-type devices.

    A station offering multiple measurement types (e.g. discharge and water
    level) creates one Home Assistant device per type, sharing the same
    station name -- without this, their device pages would be
    indistinguishable in the "Device info" card.
    """
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = measurement_type
    coordinator.data = _observation()
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("value"),
    )

    assert sensor.device_info is not None
    assert sensor.device_info["model"] == f"Hydrological monitoring station ({expected_name})"


@pytest.mark.parametrize(
    ("configured_language", "expected_model"),
    [
        ("de", "Hydrologische Messstelle (Abfluss)"),
        ("de-DE", "Hydrologische Messstelle (Abfluss)"),
        ("en", "Hydrological monitoring station (Discharge)"),
        ("fr", "Hydrological monitoring station (Discharge)"),
    ],
)
def test_device_model_localizes_to_configured_language(
    configured_language: str, expected_model: str
) -> None:
    """Test that the device model follows Home Assistant's configured language.

    Unlike entity names, device name/model text has no translation_key
    mechanism, so it must be resolved manually against hass.config.language.
    Region-qualified codes (de-DE) and unsupported languages (fr) both fall
    back sensibly (to the base language and to English respectively).
    """
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = _observation()
    coordinator.last_update_success = True
    coordinator.hass = MagicMock()
    coordinator.hass.config.language = configured_language

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("value"),
    )

    assert sensor.device_info is not None
    assert sensor.device_info["model"] == expected_model


def test_device_model_defaults_to_english_without_hass() -> None:
    """Test the fallback for test doubles / edge cases without a real hass."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = _observation()
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description("value"),
    )

    assert sensor.device_info is not None
    assert sensor.device_info["model"] == "Hydrological monitoring station (Discharge)"

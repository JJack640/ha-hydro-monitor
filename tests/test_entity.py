"""Tests for Hydro Monitor entities."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import (
    HydroDatedExtreme,
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
from custom_components.hydro_monitor.sensor_glossary import sensor_description


def _description(key: str):
    """Return one sensor description by key."""
    return next(
        description for description in SENSOR_DESCRIPTIONS if description.key == key
    )


def _attrs(sensor: HydroObservationSensor) -> dict:
    """Return a sensor's extra_state_attributes with the glossary 'description' stripped.

    The glossary description is covered by its own dedicated test
    (test_extra_state_attributes_carry_glossary_description); stripping it
    here keeps the other attribute-shape tests focused on their own
    concerns and independent of the exact glossary wording.
    """
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    return {key: value for key, value in attrs.items() if key != "description"}


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
    assert _attrs(sensor) == {
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
    assert _attrs(sensor) == {
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
    assert _attrs(sensor) == {
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
    assert _attrs(sensor) == {"error": "static down"}


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
    assert _attrs(sensor) == {
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
    assert _attrs(sensor) == {
        "error": None,
        "reference_date": "2026-07-15",
    }


_HISTORICAL_STATISTIC_SHAPED_KEYS = [
    "mq",
    "mnq",
    "mw",
    "mnw",
    "nq",
    "median_q",
    "nw",
    "median_w",
    "min_q_calendar_day",
    "median_q_calendar_day",
    "max_q_calendar_day",
    "median_w_calendar_day",
    "sum_d",
    "sum_v",
    "days_below_glw",
    "depth_below_ground",
]
# nm7q/nm30q are deliberately excluded: since Sprint 7 they also carry
# occurred_from/occurred_to attributes (see
# test_dated_extreme_sensor_exposes_error/_reports_value below), so they no
# longer share this simple {"error": ...}-only shape.


@pytest.mark.parametrize("key", _HISTORICAL_STATISTIC_SHAPED_KEYS)
def test_historical_statistic_sensor_exposes_error(key: str) -> None:
    """Test that a historical-statistic-shaped sensor surfaces its own error."""
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
    assert _attrs(sensor) == {"error": "mq down"}


@pytest.mark.parametrize("key", _HISTORICAL_STATISTIC_SHAPED_KEYS)
def test_historical_statistic_sensor_reports_value(key: str) -> None:
    """Test that a historical-statistic-shaped sensor reports its numeric value."""
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
    assert _attrs(sensor) == {"error": None}


@pytest.mark.parametrize("key", ["nm7q", "nm30q"])
def test_dated_extreme_sensor_exposes_error(key: str) -> None:
    """Test that nm7q/nm30q surface their own error, plus null occurrence dates."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
        **{key: HydroDerivedValue(error="nm7q down")},
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description(key),
    )

    assert sensor.native_value is None
    assert _attrs(sensor) == {
        "error": "nm7q down",
        "occurred_from": None,
        "occurred_to": None,
    }


@pytest.mark.parametrize("key", ["nm7q", "nm30q"])
def test_dated_extreme_sensor_reports_value_and_occurrence(key: str) -> None:
    """Test that nm7q/nm30q report their value plus the date range it occurred in."""
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
        **{
            key: HydroDerivedValue(value=15.26, unit="m³/s", error=None),
            f"{key}_dated": HydroDatedExtreme(
                value=15.26,
                unit="m³/s",
                occurred_from=date(2026, 7, 15),
                occurred_to=date(2026, 7, 21),
                raw_label="15.26 (15.07.2026-21.07.2026)",
            ),
        },
    )
    coordinator.last_update_success = True

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description(key),
    )

    assert sensor.native_value == pytest.approx(15.26)
    assert _attrs(sensor) == {
        "error": None,
        "occurred_from": "2026-07-15",
        "occurred_to": "2026-07-21",
    }


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
    assert _attrs(sensor) == {"error": "stat down"}


@pytest.mark.parametrize(
    "key",
    [
        "low_water_class",
        "official_development_7d",
        "below_glw",
        "boundary_static_extremely_low",
        "boundary_dynamic_extremely_low",
        "nm7q",
        "mq",
        "nq",
        "min_q_calendar_day",
        "sum_d",
        "days_below_glw",
        "depth_below_ground",
        "percent_of_mq",
        "decile_p50",
    ],
)
def test_extra_state_attributes_carry_glossary_description(key: str) -> None:
    """Test that official NIWIS derived-quantity sensors explain themselves.

    Their names mirror NIWIS's own abbreviations (MQ, GlW, ...), which
    aren't self-explanatory, and Home Assistant has no per-entity tooltip
    mechanism -- so every such sensor's "more info" attributes carry a
    plain-language `description` in the configured language.
    """
    coordinator = MagicMock(spec=HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = HydroMeasurementType.DISCHARGE
    coordinator.data = HydroObservation(
        measurement_type=HydroMeasurementType.DISCHARGE,
        value=10.5,
        unit="m³/s",
        observed_on=date(2026, 7, 15),
    )
    coordinator.last_update_success = True
    coordinator.hass = MagicMock()
    coordinator.hass.config.language = "de"

    sensor = HydroObservationSensor(
        coordinator=coordinator,
        description=_description(key),
    )

    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["description"] == sensor_description(key, "de")
    assert attrs["description"]


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

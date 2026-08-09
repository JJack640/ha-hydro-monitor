"""Tests for Hydro Monitor diagnostics."""

from datetime import date
from types import SimpleNamespace

import pytest

from custom_components.hydro_monitor.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.hydro_monitor.models import (
    HydroCalendarDayValue,
    HydroDatedExtreme,
    HydroDeciles,
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
        deciles=HydroDeciles(
            classification_labels=(
                "0-10%",
                "10-20%",
                "20-30%",
                "30-40%",
                "40-50%",
                "50-60%",
                "60-70%",
                "70-80%",
                "80-90%",
                "90-100%",
            ),
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
            error=None,
        ),
        mq=HydroDerivedValue(value=46.41388, unit="m³/s", error=None),
        mnq=HydroDerivedValue(value=25.013334, unit="m³/s", error=None),
        nm7q=HydroDerivedValue(value=15.257143, unit="m³/s", error=None),
        nm30q=HydroDerivedValue(value=17.503448, unit="m³/s", error=None),
        mw=HydroDerivedValue(value=88.48911, unit="cm", error=None),
        mnw=HydroDerivedValue(value=49.866665, unit="cm", error=None),
        nq=HydroDerivedValue(value=15.8, unit="m³/s", error=None),
        median_q=HydroDerivedValue(value=41.05, unit="m³/s", error=None),
        sum_d=HydroDerivedValue(value=30.0, unit="d", error=None),
        sum_v=HydroDerivedValue(value=19094400.0, unit="m³", error=None),
        days_below_glw=HydroDerivedValue(value=18.0, unit="d", error=None),
        depth_below_ground=HydroDerivedValue(value=38.9, unit="m", error=None),
        min_q_calendar_day=HydroCalendarDayValue(
            value=25.43, unit="m³/s", reference_date=date(2026, 7, 15), error=None
        ),
        median_q_calendar_day=HydroCalendarDayValue(
            value=41.05, unit="m³/s", reference_date=date(2026, 7, 15), error=None
        ),
        max_q_calendar_day=HydroCalendarDayValue(
            value=84.18, unit="m³/s", reference_date=date(2026, 7, 15), error=None
        ),
        nm7q_dated=HydroDatedExtreme(
            value=15.26,
            unit="m³/s",
            occurred_from=date(2026, 7, 15),
            occurred_to=date(2026, 7, 21),
            raw_label="15.26 (15.07.2026-21.07.2026)",
            error=None,
        ),
        below_glw="unterhalb",
        below_glw_raw="unterhalb",
        below_glw_error=None,
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

    deciles = diagnostics["observation"]["deciles"]
    assert deciles["classification_labels"] == [
        "0-10%",
        "10-20%",
        "20-30%",
        "30-40%",
        "40-50%",
        "50-60%",
        "60-70%",
        "70-80%",
        "80-90%",
        "90-100%",
    ]
    assert deciles["thresholds"] == [
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
    ]
    assert deciles["unit"] == "m³/s"
    assert deciles["reference_date"] == "2026-07-15"
    assert deciles["error"] is None

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
    assert historical_statistics["nq"] == {
        "value": pytest.approx(15.8),
        "unit": "m³/s",
        "error": None,
    }
    assert historical_statistics["median_q"] == {
        "value": pytest.approx(41.05),
        "unit": "m³/s",
        "error": None,
    }
    assert historical_statistics["nw"] is None
    assert historical_statistics["median_w"] is None
    assert historical_statistics["sum_d"] == {
        "value": pytest.approx(30.0),
        "unit": "d",
        "error": None,
    }
    assert historical_statistics["sum_v"] == {
        "value": pytest.approx(19094400.0),
        "unit": "m³",
        "error": None,
    }
    assert historical_statistics["days_below_glw"] == {
        "value": pytest.approx(18.0),
        "unit": "d",
        "error": None,
    }
    assert historical_statistics["depth_below_ground"] == {
        "value": pytest.approx(38.9),
        "unit": "m",
        "error": None,
    }

    calendar_day_statistics = diagnostics["observation"]["calendar_day_statistics"]
    assert calendar_day_statistics["min_q"] == {
        "value": pytest.approx(25.43),
        "unit": "m³/s",
        "reference_date": "2026-07-15",
        "error": None,
    }
    assert calendar_day_statistics["median_q"] == {
        "value": pytest.approx(41.05),
        "unit": "m³/s",
        "reference_date": "2026-07-15",
        "error": None,
    }
    assert calendar_day_statistics["max_q"] == {
        "value": pytest.approx(84.18),
        "unit": "m³/s",
        "reference_date": "2026-07-15",
        "error": None,
    }
    assert calendar_day_statistics["median_w"] is None

    dated_extremes = diagnostics["observation"]["dated_extremes"]
    assert dated_extremes["nm7q"] == {
        "value": pytest.approx(15.26),
        "unit": "m³/s",
        "occurred_from": "2026-07-15",
        "occurred_to": "2026-07-21",
        "raw_label": "15.26 (15.07.2026-21.07.2026)",
        "error": None,
    }
    assert dated_extremes["nm30q"] is None

    assert diagnostics["observation"]["below_glw"] == "unterhalb"
    assert diagnostics["observation"]["below_glw_raw"] == "unterhalb"
    assert diagnostics["observation"]["below_glw_error"] is None

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

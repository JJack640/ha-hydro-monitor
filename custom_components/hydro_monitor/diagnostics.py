"""Diagnostics support for Hydro Monitor."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import HydroMonitorConfigEntry
from .const import MEASUREMENT_STALE_AFTER
from .models import HydroCalendarDayValue, HydroDatedExtreme, HydroDerivedValue, HydroObservation
from .trend import trend_state


def _observation_datetime(
    observed_on: date | datetime | None,
) -> datetime | None:
    """Return an observation date as an aware UTC datetime."""
    if observed_on is None:
        return None

    if isinstance(observed_on, datetime):
        if observed_on.tzinfo is None:
            return observed_on.replace(tzinfo=UTC)

        return observed_on.astimezone(UTC)

    return datetime.combine(
        observed_on,
        time.min,
        tzinfo=UTC,
    )


def _is_stale(
    observation: HydroObservation,
) -> bool | None:
    """Return whether the latest observation is stale."""
    observed_at = _observation_datetime(observation.observed_on)

    if observed_at is None:
        return None

    return dt_util.utcnow() - observed_at >= MEASUREMENT_STALE_AFTER


def _boundaries_diagnostics(
    observation: HydroObservation,
) -> dict[str, Any] | None:
    """Return diagnostics for the official low-water classification boundaries."""
    boundaries = observation.boundaries

    if boundaries is None:
        return None

    return {
        "classification_labels": (
            list(boundaries.classification_labels)
            if boundaries.classification_labels is not None
            else None
        ),
        "open_ended": boundaries.open_ended,
        "static_thresholds": (
            list(boundaries.static_thresholds)
            if boundaries.static_thresholds is not None
            else None
        ),
        "static_unit": boundaries.static_unit,
        "static_error": boundaries.static_error,
        "dynamic_thresholds": (
            list(boundaries.dynamic_thresholds)
            if boundaries.dynamic_thresholds is not None
            else None
        ),
        "dynamic_unit": boundaries.dynamic_unit,
        "dynamic_reference_date": (
            boundaries.dynamic_reference_date.isoformat()
            if boundaries.dynamic_reference_date is not None
            else None
        ),
        "dynamic_error": boundaries.dynamic_error,
    }


def _deciles_diagnostics(
    observation: HydroObservation,
) -> dict[str, Any] | None:
    """Return diagnostics for the official NIWIS deciles."""
    deciles = observation.deciles

    if deciles is None:
        return None

    return {
        "classification_labels": (
            list(deciles.classification_labels)
            if deciles.classification_labels is not None
            else None
        ),
        "thresholds": (
            list(deciles.thresholds) if deciles.thresholds is not None else None
        ),
        "unit": deciles.unit,
        "reference_date": (
            deciles.reference_date.isoformat()
            if deciles.reference_date is not None
            else None
        ),
        "error": deciles.error,
    }


def _historical_statistic_diagnostics(
    stat: HydroDerivedValue | None,
) -> dict[str, Any] | None:
    """Return diagnostics for one historical-statistics quantity."""
    if stat is None:
        return None

    return {"value": stat.value, "unit": stat.unit, "error": stat.error}


def _calendar_day_diagnostics(
    stat: HydroCalendarDayValue | None,
) -> dict[str, Any] | None:
    """Return diagnostics for one historical calendar-day quantity."""
    if stat is None:
        return None

    return {
        "value": stat.value,
        "unit": stat.unit,
        "reference_date": (
            stat.reference_date.isoformat() if stat.reference_date is not None else None
        ),
        "error": stat.error,
    }


def _dated_extreme_diagnostics(
    dated: HydroDatedExtreme | None,
) -> dict[str, Any] | None:
    """Return diagnostics for one NM7Q/NM30Q 'mit Datum' quantity."""
    if dated is None:
        return None

    return {
        "value": dated.value,
        "unit": dated.unit,
        "occurred_from": (
            dated.occurred_from.isoformat() if dated.occurred_from is not None else None
        ),
        "occurred_to": (
            dated.occurred_to.isoformat() if dated.occurred_to is not None else None
        ),
        "raw_label": dated.raw_label,
        "error": dated.error,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: HydroMonitorConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a Hydro Monitor config entry."""
    runtime_data = entry.runtime_data
    station = runtime_data.station
    coordinator = runtime_data.coordinator
    observation = coordinator.data

    return {
        "config_entry": {
            "title": entry.title,
            "provider": station.provider,
            "station_id": station.station_id,
            "measurement_type": coordinator.measurement_type.value,
        },
        "station": {
            "name": station.name,
            "country_code": station.country_code,
            "station_type": station.station_type,
            "locality": station.locality,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "distance_km": station.distance_km,
            "waterbody": station.waterbody,
            "waterbody_code": station.waterbody_code,
            "waterbody_position": station.waterbody_position,
            "catchment_area_km2": station.catchment_area_km2,
            "elevation_ground": station.elevation_ground,
            "gauge_zero_elevation": station.gauge_zero_elevation,
            "elevation_system": station.elevation_system,
            "hydrogeological_region": station.hydrogeological_region,
            "hydrogeological_region_code": (station.hydrogeological_region_code),
            "operator": station.operator,
            "operator_url": station.operator_url,
            "institution": station.institution,
            "institution_url": station.institution_url,
            "source_url": station.source_url,
            "license": station.license_name,
            "remarks": station.remarks,
            "historical_low_discharge": (station.historical_low_discharge),
            "historical_low_discharge_date": (
                station.historical_low_discharge_date.isoformat()
                if station.historical_low_discharge_date is not None
                else None
            ),
            "historical_low_water_level": (station.historical_low_water_level),
            "historical_low_water_level_date": (
                station.historical_low_water_level_date.isoformat()
                if station.historical_low_water_level_date is not None
                else None
            ),
            "supported_measurement_types": [
                measurement_type.value for measurement_type in station.measurement_types
            ],
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": (
                str(coordinator.last_exception)
                if coordinator.last_exception is not None
                else None
            ),
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval is not None
                else None
            ),
        },
        "observation": (
            {
                "measurement_type": observation.measurement_type.value,
                "value": observation.value,
                "unit": observation.unit,
                "native_unit": observation.unit,
                "observed_on": (
                    observation.observed_on.isoformat()
                    if observation.observed_on is not None
                    else None
                ),
                "is_stale": _is_stale(observation),
                "trend_state": trend_state(observation),
                "quality_flag": observation.quality_flag,
                "change_1d": observation.change_1d,
                "change_7d": observation.change_7d,
                "minimum_30d": observation.minimum_30d,
                "maximum_30d": observation.maximum_30d,
                "sample_count": observation.sample_count,
                "low_water_class": observation.low_water_class,
                "low_water_class_raw": observation.low_water_class_raw,
                "low_water_class_error": observation.low_water_class_error,
                "official_development_7d": observation.official_development_7d,
                "official_development_7d_raw": observation.official_development_7d_raw,
                "official_development_7d_error": (
                    observation.official_development_7d_error
                ),
                "below_glw": observation.below_glw,
                "below_glw_raw": observation.below_glw_raw,
                "below_glw_error": observation.below_glw_error,
                "boundaries": _boundaries_diagnostics(observation),
                "deciles": _deciles_diagnostics(observation),
                "historical_statistics": {
                    "mq": _historical_statistic_diagnostics(observation.mq),
                    "mnq": _historical_statistic_diagnostics(observation.mnq),
                    "nm7q": _historical_statistic_diagnostics(observation.nm7q),
                    "nm30q": _historical_statistic_diagnostics(observation.nm30q),
                    "mw": _historical_statistic_diagnostics(observation.mw),
                    "mnw": _historical_statistic_diagnostics(observation.mnw),
                    "nq": _historical_statistic_diagnostics(observation.nq),
                    "median_q": _historical_statistic_diagnostics(observation.median_q),
                    "nw": _historical_statistic_diagnostics(observation.nw),
                    "median_w": _historical_statistic_diagnostics(observation.median_w),
                    "sum_d": _historical_statistic_diagnostics(observation.sum_d),
                    "sum_v": _historical_statistic_diagnostics(observation.sum_v),
                    "days_below_glw": _historical_statistic_diagnostics(
                        observation.days_below_glw
                    ),
                    "depth_below_ground": _historical_statistic_diagnostics(
                        observation.depth_below_ground
                    ),
                },
                "calendar_day_statistics": {
                    "min_q": _calendar_day_diagnostics(observation.min_q_calendar_day),
                    "median_q": _calendar_day_diagnostics(
                        observation.median_q_calendar_day
                    ),
                    "max_q": _calendar_day_diagnostics(observation.max_q_calendar_day),
                    "median_w": _calendar_day_diagnostics(
                        observation.median_w_calendar_day
                    ),
                },
                "dated_extremes": {
                    "nm7q": _dated_extreme_diagnostics(observation.nm7q_dated),
                    "nm30q": _dated_extreme_diagnostics(observation.nm30q_dated),
                },
            }
            if observation is not None
            else None
        ),
    }

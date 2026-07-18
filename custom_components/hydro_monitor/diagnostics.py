"""Diagnostics support for Hydro Monitor."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import HydroMonitorConfigEntry
from .const import MEASUREMENT_STALE_AFTER
from .models import HydroObservation


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


def _trend_state(
    observation: HydroObservation,
) -> str | None:
    """Return the categorized seven-day trend state."""
    change = observation.change_7d

    if change is None:
        return None

    change_mm = change * 1000

    if change_mm >= 25:
        return "strong_rising"

    if change_mm >= 2:
        return "rising"

    if change_mm <= -25:
        return "strong_falling"

    if change_mm <= -2:
        return "falling"

    return "stable"


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
            "waterbody": station.waterbody,
            "operator": station.operator,
            "institution": station.institution,
            "source_url": station.source_url,
            "license": station.license_name,
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
                "trend_state": _trend_state(observation),
                "quality_flag": observation.quality_flag,
                "change_1d": observation.change_1d,
                "change_7d": observation.change_7d,
                "minimum_30d": observation.minimum_30d,
                "maximum_30d": observation.maximum_30d,
                "sample_count": observation.sample_count,
            }
            if observation is not None
            else None
        ),
    }

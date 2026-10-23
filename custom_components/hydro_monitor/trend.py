"""Trend values, icons and states, judged in the unit of each measurement type.

NIWIS reports groundwater in metres, water level in centimetres, discharge in
m³/s and spring discharge in l/s. A trend therefore cannot be judged against
one fixed millimetre scale: levels are judged by their absolute change,
discharges by their relative change.
"""

from __future__ import annotations

import math
from typing import Final

from .models import HydroMeasurementType, HydroObservation

_METRES_PER_UNIT: Final = {"m": 1.0, "cm": 0.01, "mm": 0.001}

# Default unit per level type, used when an observation carries no known unit.
_LEVEL_DEFAULT_UNIT: Final = {
    HydroMeasurementType.GROUNDWATER_LEVEL: "m",
    HydroMeasurementType.WATER_LEVEL: "cm",
}

# (stable below, moderate from, strong from), as an absolute change in metres.
_LEVEL_THRESHOLDS_M: Final = {
    HydroMeasurementType.GROUNDWATER_LEVEL: (0.002, 0.010, 0.025),
    HydroMeasurementType.WATER_LEVEL: (0.01, 0.05, 0.25),
}

# (stable below, moderate from, strong from), as a percentage of the earlier
# value. Used for discharge and spring discharge, whose scale differs by
# orders of magnitude between stations.
_RELATIVE_THRESHOLDS_PCT: Final = (2.0, 10.0, 25.0)

_NEUTRAL_ICON: Final = "mdi:trending-neutral"


def _metres_per_unit(observation: HydroObservation) -> float:
    """Return how many metres one unit of a level observation is."""
    default_unit = _LEVEL_DEFAULT_UNIT[observation.measurement_type]
    # "m. ü. NHN" is a level relative to a datum; its change is plain metres.
    token = (observation.unit or default_unit).split()[0].rstrip(".")

    return _METRES_PER_UNIT.get(token, _METRES_PER_UNIT[default_unit])


def _thresholds(
    measurement_type: HydroMeasurementType,
) -> tuple[float, float, float]:
    """Return the stable, moderate and strong thresholds for a type."""
    return _LEVEL_THRESHOLDS_M.get(measurement_type, _RELATIVE_THRESHOLDS_PCT)


def _score(
    observation: HydroObservation,
    change: float | None,
) -> float | None:
    """Return a change on the threshold scale of its measurement type.

    Metres for levels, percent of the earlier value for discharges.
    """
    if change is None:
        return None

    if observation.measurement_type in _LEVEL_THRESHOLDS_M:
        return round(change * _metres_per_unit(observation), 9)

    if observation.value is None:
        return None

    earlier = observation.value - change

    if earlier <= 0:
        # Flow starting from nothing is as strong a rise as there can be.
        return math.copysign(math.inf, change) if change else 0.0

    return round(change / earlier * 100, 9)


def trend_unit(observation: HydroObservation) -> str | None:
    """Return the unit of the trend sensors for an observation.

    Groundwater trends are small, so they stay in millimetres. Everything
    else is shown in the unit of the measurement itself.
    """
    if observation.measurement_type is HydroMeasurementType.GROUNDWATER_LEVEL:
        return "mm"

    return observation.unit


def trend_value(
    observation: HydroObservation,
    change: float | None,
) -> float | int | None:
    """Return a change in the unit given by `trend_unit`."""
    if change is None:
        return None

    if observation.measurement_type is HydroMeasurementType.GROUNDWATER_LEVEL:
        return round(change * _metres_per_unit(observation) * 1000)

    return round(change, 3)


def trend_icon(
    observation: HydroObservation,
    change: float | None,
) -> str:
    """Return a direction and strength icon for a change."""
    score = _score(observation, change)

    if score is None:
        return _NEUTRAL_ICON

    stable, moderate, strong = _thresholds(observation.measurement_type)
    magnitude = abs(score)

    if magnitude < stable:
        return _NEUTRAL_ICON

    direction = "up" if score > 0 else "down"

    if magnitude >= strong:
        return f"mdi:arrow-{direction}-bold"

    if magnitude >= moderate:
        return f"mdi:arrow-{direction}"

    return f"mdi:arrow-{direction}-thin"


def trend_state(observation: HydroObservation) -> str | None:
    """Return the categorized seven-day trend state."""
    score = _score(observation, observation.change_7d)

    if score is None:
        return None

    stable, _moderate, strong = _thresholds(observation.measurement_type)

    if score >= strong:
        return "strong_rising"

    if score >= stable:
        return "rising"

    if score <= -strong:
        return "strong_falling"

    if score <= -stable:
        return "falling"

    return "stable"

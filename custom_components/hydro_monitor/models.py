"""Data models for the Hydro Monitor integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class HydroMeasurementType(StrEnum):
    """Supported hydrological measurement types."""

    DISCHARGE = "discharge"
    WATER_LEVEL = "water_level"
    GROUNDWATER_LEVEL = "groundwater_level"
    SPRING_DISCHARGE = "spring_discharge"


@dataclass(frozen=True, slots=True)
class HydroStation:
    """Represent a hydrological monitoring station."""

    provider: str
    station_id: str
    name: str
    measurement_types: tuple[HydroMeasurementType, ...]

    latitude: float | None = None
    longitude: float | None = None
    waterbody: str | None = None
    operator: str | None = None
    institution: str | None = None
    source_url: str | None = None
    license_name: str | None = None
    distance_km: float | None = None


@dataclass(frozen=True, slots=True)
class HydroObservation:
    """Represent a processed hydrological observation."""

    measurement_type: HydroMeasurementType
    value: float | None
    unit: str | None
    observed_on: date | None

    quality_flag: str | None = None

    change_1d: float | None = None
    change_7d: float | None = None

    minimum_30d: float | None = None
    maximum_30d: float | None = None

    sample_count: int = 0

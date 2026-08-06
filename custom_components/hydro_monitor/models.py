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

    country_code: str | None = None
    station_type: str | None = None
    locality: str | None = None

    waterbody: str | None = None
    waterbody_code: str | None = None
    waterbody_position: str | None = None
    catchment_area_km2: float | None = None

    elevation_ground: float | None = None
    gauge_zero_elevation: float | None = None
    elevation_system: str | None = None

    hydrogeological_region: str | None = None
    hydrogeological_region_code: str | None = None

    operator: str | None = None
    operator_url: str | None = None
    institution: str | None = None
    institution_url: str | None = None

    source_url: str | None = None
    license_name: str | None = None
    remarks: str | None = None

    historical_low_discharge: float | None = None
    historical_low_discharge_date: date | None = None
    historical_low_water_level: float | None = None
    historical_low_water_level_date: date | None = None

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

    low_water_class: str | None = None
    # Preserves either NIWIS's official `fehlermeldung`, or (if the
    # classification request itself failed at the transport level) a local
    # description of that failure. See providers/niwis/mapper.py.
    low_water_class_error: str | None = None

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
class HydroLowWaterBoundaries:
    """Represent official NIWIS low-water classification boundaries.

    Static and dynamic boundaries are fetched, cached and can fail
    independently, hence the separate static_*/dynamic_* halves.
    classification_labels/open_ended are shared metadata sourced from
    whichever half succeeded (preferring static); NIWIS returns identical
    values for both endpoints in every observed sample, but this is not
    guaranteed by documentation.
    """

    classification_labels: tuple[str, ...] | None = None
    open_ended: bool | None = None  # NIWIS beidseitigOffeneSchwellenwerte

    static_thresholds: tuple[float, ...] | None = None
    static_unit: str | None = None
    static_error: str | None = None

    dynamic_thresholds: tuple[float, ...] | None = None
    dynamic_unit: str | None = None
    dynamic_reference_date: date | None = None
    dynamic_error: str | None = None


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
    # The raw NIWIS label as received (e.g. "extrem niedrig"), preserved
    # even when the mapped low_water_class key is suppressed. See ADR-005
    # in docs/niwis_reference.md ("preserve unknown values").
    low_water_class_raw: str | None = None
    # Preserves either NIWIS's official `fehlermeldung`, or (if the
    # classification request itself failed at the transport level) a local
    # description of that failure. See providers/niwis/mapper.py.
    low_water_class_error: str | None = None

    boundaries: HydroLowWaterBoundaries | None = None

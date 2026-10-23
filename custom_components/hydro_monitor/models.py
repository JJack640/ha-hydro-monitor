"""Data models for the Hydro Monitor integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
class HydroDerivedValue:
    """Represent one numeric derived-quantity result from a provider.

    A minimal, deliberately trimmed instance of the HydroDerivedValue
    concept sketched in docs/ARCHITECTURE.md §4 -- source/reference_period/
    observed_on/quality are omitted since HydroReferencePeriod/HydroQuality
    don't exist yet and would be premature to build for one sprint.
    """

    value: float | None = None
    unit: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class HydroDeciles:
    """Represent official NIWIS decile boundaries (10-class, dynamic-only).

    No static counterpart exists in the NIWIS catalog, so unlike
    HydroLowWaterBoundaries there is no static/dynamic split -- this
    always represents the per-day table's "today" row. thresholds has 11
    points (not the len(labels)-1 formula used for open-ended boundaries):
    berechneKlassifikationsgrenzeDynamisch returns
    beidseitigOffeneSchwellenwerte=False for deciles (closed on both
    ends), so thresholds[0]/[10] are the reference period's absolute
    min/max, with 9 interior points dividing the 10 bands.
    """

    classification_labels: tuple[str, ...] | None = None  # "0-10%".."90-100%"
    thresholds: tuple[float, ...] | None = None
    unit: str | None = None
    reference_date: date | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class HydroCalendarDayValue:
    """One value from a NIWIS per-calendar-day table (berechneZeitreihenErgebnisNummer).

    E.g. the historical median/min/max discharge recorded on this exact
    calendar day across the reference period. Day-of-year indexed and
    cached once per day, like HydroDeciles/dynamic HydroLowWaterBoundaries
    -- but each row is a single plain number, not a set of thresholds.
    """

    value: float | None = None
    unit: str | None = None
    reference_date: date | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class HydroDatedExtreme:
    """A derived value bundled with the date range it occurred in.

    NIWIS's "mit Datum" quantities (e.g. NM7Q mit Datum) return a single
    composite string ("15.26 (15.07.2026-21.07.2026)") combining the value
    with the date range it occurred in.
    """

    value: float | None = None
    unit: str | None = None
    occurred_from: date | None = None
    occurred_to: date | None = None
    raw_label: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class HydroObservation:
    """Represent a processed hydrological observation."""

    measurement_type: HydroMeasurementType
    value: float | None
    unit: str | None
    # A calendar day for daily providers, a point in time for finer ones.
    observed_on: date | datetime | None

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

    # Official NIWIS "development over the last 7 days" (Abfluss/Wasserstand
    # only). Distinct from the locally-calculated change_7d/trend_state
    # above: this is NIWIS's own categorical assessment, not a Hydro
    # Monitor computation. The vocabulary is unconfirmed (only
    # "gleichbleibend" observed so far), so the value is the raw NIWIS
    # label, not a mapped key.
    official_development_7d: str | None = None
    official_development_7d_raw: str | None = None
    official_development_7d_error: str | None = None

    # Official NIWIS historical statistics (berechneEinzelwertNummer).
    # MQ/MNQ/NM7Q/NM30Q are discharge-only; MW/MNW are their water_level
    # equivalents (mean / mean-low value). None for groundwater_level and
    # spring_discharge, which have no entries in this endpoint family.
    mq: HydroDerivedValue | None = None
    mnq: HydroDerivedValue | None = None
    nm7q: HydroDerivedValue | None = None
    nm30q: HydroDerivedValue | None = None
    mw: HydroDerivedValue | None = None
    mnw: HydroDerivedValue | None = None

    # Official NIWIS deciles (berechneKlassifikationsgrenzeDynamisch,
    # "... Dezile tageweise"). Discharge/water_level only. See
    # HydroDeciles for why this has no static/dynamic split.
    deciles: HydroDeciles | None = None

    # Official NIWIS historical calendar-day envelope
    # (berechneZeitreihenErgebnisNummer, "... pro Kalendertag"/
    # "...Kalendartag"): the historical min/median/max value recorded on
    # this exact calendar day across the reference period. Day-of-year
    # indexed and day-scoped cached, like the dynamic boundaries/deciles
    # above -- but a plain number per day, not a set of thresholds.
    # min_q/median_q/max_q are discharge-only; median_w is its water_level
    # equivalent (no min_w/max_w entry exists in the NIWIS catalog).
    min_q_calendar_day: HydroCalendarDayValue | None = None
    median_q_calendar_day: HydroCalendarDayValue | None = None
    max_q_calendar_day: HydroCalendarDayValue | None = None
    median_w_calendar_day: HydroCalendarDayValue | None = None

    # Official NIWIS reference-period single values (berechneEinzelwertNummer,
    # same shape/endpoint as mq/mnq/mw/mnw above). NQ/median_q are
    # discharge-only (absolute low / median across the reference period,
    # not day-indexed -- distinct from median_q_calendar_day above despite
    # the similar NIWIS name); NW/median_w are their water_level
    # equivalents.
    nq: HydroDerivedValue | None = None
    median_q: HydroDerivedValue | None = None
    nw: HydroDerivedValue | None = None
    median_w: HydroDerivedValue | None = None

    # Official NIWIS NM7Q/NM30Q bundled with the date range they occurred
    # in ("... mit Datum", berechneEinzelwertKategorie). Discharge-only,
    # same interval-based fetch as nm7q/nm30q above. Exposed as attributes
    # on the nm7q/nm30q sensors rather than separate entities.
    nm7q_dated: HydroDatedExtreme | None = None
    nm30q_dated: HydroDatedExtreme | None = None

    # Official NIWIS station-specific low-water day/volume accumulation
    # over the same 30-day window as nm7q/nm30q ("SumD Zeitfenster"/"SumV
    # Zeitfenster", berechneEinzelwertNummer). Discharge-only. The
    # per-station analogue of the blocked nationwide climate indicator
    # (see docs/niwis_reference.md 8.3) -- live-verified as a genuine
    # cumulative low-water-day counter, not a trivial day index.
    sum_d: HydroDerivedValue | None = None
    sum_v: HydroDerivedValue | None = None

    # Official NIWIS federal-waterway navigation indicators
    # ("unter GlW"/"Tage unter GlWRNW/BWu aktueller Tag"). Water_level
    # only, and narrowly applicable even then -- live-verified real only
    # at federal-waterway (DEXX-landcode) gauges, empty/error elsewhere.
    # below_glw mirrors official_development_7d's raw-label-passthrough
    # shape (vocabulary beyond "unterhalb" is unconfirmed).
    below_glw: str | None = None
    below_glw_raw: str | None = None
    below_glw_error: str | None = None
    days_below_glw: HydroDerivedValue | None = None

    # Official NIWIS groundwater depth below ground surface ("m unter
    # Geländeoberkante", berechneZeitreihenErgebnisNummer + 30-day
    # interval). Groundwater_level only. Uses NIWIS's own endpoint rather
    # than computing elevation_ground - value locally: a live test station
    # had elevation_ground=null while this endpoint still returned real
    # values for it.
    depth_below_ground: HydroDerivedValue | None = None

    # PEGELONLINE's own classification of the current water level against
    # the mean low and mean high water of the gauge (MNW/MHW): "low",
    # "normal" or "high". `level_state_raw` keeps the service's value (it
    # also says "unknown", "commented" and "out-dated", which map to None).
    # Water level only; None for providers that do not report it.
    level_state: str | None = None
    level_state_raw: str | None = None
    level_state_error: str | None = None

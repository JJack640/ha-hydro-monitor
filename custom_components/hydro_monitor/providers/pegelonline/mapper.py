"""Map PEGELONLINE responses to Hydro Monitor models."""

from __future__ import annotations

import math
import re
from bisect import bisect_right
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from ...models import HydroMeasurementType, HydroObservation, HydroStation
from .const import (
    LICENSE_NAME,
    PEGELONLINE_TIMESERIES_TO_HYDRO,
    STATION_PAGE_URL,
)

# Abbreviations that stay upper case when a name is converted from the
# service's upper-case spelling: OP/UP = Oberpegel/Unterpegel (above/below a
# lock or weir), OW/UW = Oberwasser/Unterwasser, and the like.
_UPPERCASE_TOKENS: Final = frozenset(
    {
        "AP", "AWK", "BHV", "BP", "DFH", "EP", "ESK", "GW", "KM", "LFK",
        "MPM", "NOK", "NWS", "OHV", "OIE", "OOG", "OP", "OW", "SHW", "SP",
        "UF", "UP", "UW", "WHV", "ABZ",
    }
)  # fmt: skip

_WORD: Final = re.compile(r"[^\W\d_]+|\d+|\W+|_+", re.UNICODE)

# PEGELONLINE's own wording for the water level against MNW/MHW. Anything
# else ("unknown", "commented", "out-dated") means there is no usable state.
_LEVEL_STATES: Final = frozenset({"low", "normal", "high"})

# Trends compare the mean of the last 24 hours with the mean of the 24 hours
# a day (a week) earlier, not two single readings. Tidal gauges swing by
# several metres twice a day, so two readings only tell the phase of the tide;
# daily means hold on to the level. It also matches NIWIS, whose series are
# daily values. Measured at Hamburg St. Pauli: the spread of the 1-day change
# halves compared with two single readings.
_TREND_WINDOW: Final = timedelta(hours=24)


def display_name(shortname: str | None, longname: str | None) -> str | None:
    """Return a readable station or waterbody name.

    The service gives each name twice: `shortname`, which is often properly
    cased ("Roßdorf"), and `longname` in capitals ("ROSSDORF"). Use the
    properly cased one when there is one. When both are in capitals, convert
    the long one: the short one can be an abbreviation ("DHK" for
    "DATTELN-HAMM-KANAL").
    """
    for candidate in (shortname, longname):
        if candidate and candidate != candidate.upper():
            return candidate.replace("_", " ").strip()

    name = (longname or shortname or "").replace("_", " ").strip()

    if not name:
        return None

    def convert(match: re.Match[str]) -> str:
        token = match.group(0)

        if token.upper() in _UPPERCASE_TOKENS:
            return token.upper()

        if token.isalpha():
            return token.capitalize()

        return token

    return _WORD.sub(convert, name)


def _as_float(value: Any) -> float | None:
    """Convert a value to a finite float."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    return result if math.isfinite(result) else None


def _timeseries(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a station's time series by short name."""
    return {
        item["shortname"]: item
        for item in data.get("timeseries") or []
        if isinstance(item, dict) and item.get("shortname")
    }


def station_from_pegelonline(
    data: dict[str, Any],
    distance_km: float | None = None,
) -> HydroStation:
    """Map a PEGELONLINE station record."""
    series = _timeseries(data)
    measurement_types = tuple(
        measurement_type
        for measurement_type in HydroMeasurementType
        if any(
            PEGELONLINE_TIMESERIES_TO_HYDRO.get(name) is measurement_type
            for name in series
        )
    )

    water = data.get("water") if isinstance(data.get("water"), dict) else {}
    water_level = series.get("W", {})
    gauge_zero = water_level.get("gaugeZero")
    gauge_zero = gauge_zero if isinstance(gauge_zero, dict) else {}
    number = data.get("number")
    kilometre = _as_float(data.get("km"))

    return HydroStation(
        provider="pegelonline",
        station_id=str(data["uuid"]),
        name=display_name(data.get("shortname"), data.get("longname"))
        or str(data["uuid"]),
        measurement_types=measurement_types,
        latitude=_as_float(data.get("latitude")),
        longitude=_as_float(data.get("longitude")),
        waterbody=display_name(water.get("shortname"), water.get("longname")),
        waterbody_position=None if kilometre is None else str(kilometre),
        gauge_zero_elevation=_as_float(gauge_zero.get("value")),
        elevation_system=gauge_zero.get("unit"),
        operator=data.get("agency") or None,
        license_name=LICENSE_NAME,
        source_url=(
            f"{STATION_PAGE_URL}?pegelnr={number}" if number else None
        ),
        distance_km=distance_km,
    )


def level_state_from_pegelonline(
    current: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    """Return the MNW/MHW state and the service's raw value.

    The state is None unless the service says low, normal or high.
    """
    raw = current.get("stateMnwMhw") if isinstance(current, dict) else None

    if not isinstance(raw, str):
        return None, None

    return (raw if raw in _LEVEL_STATES else None), raw


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse a PEGELONLINE timestamp into an aware UTC datetime.

    The service writes the local time with its offset (+01:00 / +02:00).
    """
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def observation_from_pegelonline(
    measurement_type: HydroMeasurementType,
    measurements: list[dict[str, Any]],
    unit: str | None,
) -> HydroObservation:
    """Map the newest valid measurement and calculate trends and extremes.

    The service delivers raw values every 1 to 15 minutes. `value` is the
    newest one. The trends are the difference between the mean of the last
    24 hours and the mean of the 24 hours one day (one week) earlier; the
    extremes are the lowest and highest raw values of the last 30 days.
    """
    valid: list[tuple[datetime, float]] = []

    for item in measurements:
        timestamp = _parse_timestamp(item.get("timestamp"))
        value = _as_float(item.get("value"))

        if timestamp is not None and value is not None:
            valid.append((timestamp, value))

    if not valid:
        return HydroObservation(measurement_type, None, unit, None, sample_count=0)

    valid.sort(key=lambda point: point[0])
    timestamps = [timestamp for timestamp, _value in valid]
    values = [value for _timestamp, value in valid]
    observed_at, value = valid[-1]

    def mean_between(start: datetime, end: datetime) -> float | None:
        """Return the mean of the values in the window (start, end]."""
        window = values[bisect_right(timestamps, start) : bisect_right(timestamps, end)]

        return math.fsum(window) / len(window) if window else None

    current_mean = mean_between(observed_at - _TREND_WINDOW, observed_at)

    def change_since(days: int) -> float | None:
        """Return the change of the 24-hour mean against `days` earlier."""
        end = observed_at - timedelta(days=days)
        earlier_mean = mean_between(end - _TREND_WINDOW, end)

        if current_mean is None or earlier_mean is None:
            return None

        return current_mean - earlier_mean

    window = [
        candidate
        for timestamp, candidate in valid
        if timestamp >= observed_at - timedelta(days=30)
    ]

    return HydroObservation(
        measurement_type,
        value,
        unit,
        observed_at,
        change_1d=change_since(1),
        change_7d=change_since(7),
        minimum_30d=min(window),
        maximum_30d=max(window),
        sample_count=len(valid),
    )

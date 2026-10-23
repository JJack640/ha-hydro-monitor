"""Tests for the PEGELONLINE mapper, mostly against real captures."""

import math
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType
from custom_components.hydro_monitor.providers.pegelonline.mapper import (
    display_name,
    level_state_from_pegelonline,
    observation_from_pegelonline,
    station_from_pegelonline,
)
from tests import pegelonline_fixtures as fixtures

WATER_LEVEL = HydroMeasurementType.WATER_LEVEL
DISCHARGE = HydroMeasurementType.DISCHARGE


@pytest.mark.parametrize(
    ("shortname", "longname", "expected"),
    [
        # Both spellings in capitals: convert, keep the abbreviations.
        ("KAUB", "KAUB", "Kaub"),
        ("HAMM UW", "HAMM UW", "Hamm UW"),
        ("BERLIN-PLÖTZENSEE OP", "BERLIN-PLÖTZENSEE OP", "Berlin-Plötzensee OP"),
        ("HAMBURG ST. PAULI", "HAMBURG ST. PAULI", "Hamburg St. Pauli"),
        ("FRANKFURT1 (ODER)", "FRANKFURT1 (ODER)", "Frankfurt1 (Oder)"),
        ("D1 HANSKALBSAND OBERFLÄCHE", "D1 HANSKALBSAND OBERFLÄCHE", "D1 Hanskalbsand Oberfläche"),
        # The properly cased short name wins, it even has the ß.
        ("Roßdorf", "ROSSDORF", "Roßdorf"),
        ("Giessen Klärwerk", "GIESSEN KLÄRWERK", "Giessen Klärwerk"),
        # An abbreviated short name loses against the long name.
        ("DHK", "DATTELN-HAMM-KANAL", "Datteln-Hamm-Kanal"),
        # Underscores become spaces.
        ("Alte_Maas", "ALTE MAAS", "Alte Maas"),
        ("ALTE_MAAS", "ALTE_MAAS", "Alte Maas"),
        # Missing parts.
        (None, "KAUB", "Kaub"),
        ("KAUB", None, "Kaub"),
        (None, None, None),
        ("", "", None),
    ],
)
def test_display_name(
    shortname: str | None, longname: str | None, expected: str | None
) -> None:
    """Test station and waterbody names are made readable."""
    assert display_name(shortname, longname) == expected


def test_station_with_both_series() -> None:
    """Test Kaub: a station with water level and discharge."""
    station = station_from_pegelonline(fixtures.station(fixtures.KAUB))

    assert station.provider == "pegelonline"
    assert station.station_id == fixtures.KAUB
    assert station.name == "Kaub"
    assert station.waterbody == "Rhein"
    assert station.waterbody_position == "546.23"
    assert station.latitude == pytest.approx(50.085438)
    assert station.longitude == pytest.approx(7.764962)
    assert station.operator == "STANDORT BINGEN"
    assert station.gauge_zero_elevation == pytest.approx(67.669)
    assert station.elevation_system == "m. ü. NHN"
    assert station.license_name == "DL-DE->Zero-2.0"
    assert station.source_url == (
        "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=25700100"
    )
    # In the order of HydroMeasurementType, not of the service's series.
    assert station.measurement_types == (DISCHARGE, WATER_LEVEL)


def test_station_with_water_level_only() -> None:
    """Test a water-level gauge has no discharge type."""
    station = station_from_pegelonline(fixtures.station(fixtures.AHLDEN))

    assert station.measurement_types == (WATER_LEVEL,)


def test_station_with_discharge_only_and_no_coordinates() -> None:
    """Test a station without coordinates maps, with None for the position."""
    station = station_from_pegelonline(fixtures.station(fixtures.PRELOUC))

    assert station.measurement_types == (DISCHARGE,)
    assert station.latitude is None
    assert station.longitude is None


def test_station_without_water_level_or_discharge_has_no_type() -> None:
    """Test a station offering only other series (e.g. temperature) has none."""
    station = station_from_pegelonline(fixtures.station(fixtures.ABBENFLETH))

    assert station.measurement_types == ()


def test_station_keeps_the_distance_it_is_given() -> None:
    """Test the optional distance argument."""
    station = station_from_pegelonline(fixtures.station(fixtures.KAUB), 12.3)

    assert station.distance_km == 12.3


def test_station_survives_missing_optional_fields() -> None:
    """Test a bare record does not raise."""
    station = station_from_pegelonline({"uuid": "u1", "longname": "TEST"})

    assert station.station_id == "u1"
    assert station.name == "Test"
    assert station.waterbody is None
    assert station.waterbody_position is None
    assert station.source_url is None
    assert station.measurement_types == ()


def test_station_name_falls_back_to_the_uuid() -> None:
    """Test a station without any name is still usable."""
    assert station_from_pegelonline({"uuid": "u1"}).name == "u1"


# --- observations ------------------------------------------------------------


def _point(timestamp: str, value: object) -> dict[str, object]:
    return {"timestamp": timestamp, "value": value}


def test_real_kaub_water_level() -> None:
    """Test a full 31-day capture against an independent calculation.

    Value is the newest raw reading; the trends are differences of 24-hour
    means; the extremes are raw minima and maxima of the last 30 days.
    """
    raw = fixtures.measurements(fixtures.KAUB, "W")
    observation = observation_from_pegelonline(WATER_LEVEL, raw, "cm")

    points = [
        (datetime.fromisoformat(item["timestamp"]).astimezone(UTC), item["value"])
        for item in raw
    ]
    newest = points[-1][0]

    def mean(start: datetime, end: datetime) -> float:
        window = [v for t, v in points if start < t <= end]
        return sum(window) / len(window)

    day = timedelta(days=1)
    current = mean(newest - day, newest)

    assert observation.measurement_type is WATER_LEVEL
    assert observation.unit == "cm"
    assert observation.value == raw[-1]["value"]
    assert observation.observed_on == newest
    assert observation.observed_on.tzinfo is not None
    assert observation.change_1d == pytest.approx(
        current - mean(newest - 2 * day, newest - day)
    )
    assert observation.change_7d == pytest.approx(
        current - mean(newest - 8 * day, newest - 7 * day)
    )
    window = [v for t, v in points if t >= newest - timedelta(days=30)]
    assert observation.minimum_30d == min(window)
    assert observation.maximum_30d == max(window)
    assert observation.sample_count == len(raw)
    assert observation.quality_flag is None


def test_real_kaub_discharge() -> None:
    """Test the discharge series of the same station."""
    raw = fixtures.measurements(fixtures.KAUB, "Q")
    observation = observation_from_pegelonline(DISCHARGE, raw, "m³/s")

    assert observation.value == raw[-1]["value"]
    assert observation.unit == "m³/s"
    assert observation.change_7d is not None


def test_real_station_in_metres_above_datum() -> None:
    """Test the unit given by the time series is carried, not assumed to be cm."""
    unit = fixtures.timeseries(fixtures.HAMM_UW, "W")["unit"]
    observation = observation_from_pegelonline(
        WATER_LEVEL, fixtures.measurements(fixtures.HAMM_UW, "W"), unit
    )

    assert unit == "m+NN"
    assert observation.unit == "m+NN"
    assert observation.value is not None


def test_timestamps_are_converted_to_utc() -> None:
    """Test the service's local time with offset becomes UTC."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            _point("2026-10-23T12:45:00+02:00", 20.0),
            _point("2026-10-23T13:00:00+02:00", 21.0),
        ],
        "cm",
    )

    assert observation.observed_on == datetime(2026, 10, 23, 11, 0, tzinfo=UTC)


def test_winter_offset_is_converted_too() -> None:
    """Test +01:00 (winter time)."""
    observation = observation_from_pegelonline(
        WATER_LEVEL, [_point("2026-12-01T13:00:00+01:00", 21.0)], "cm"
    )

    assert observation.observed_on == datetime(2026, 12, 1, 12, 0, tzinfo=UTC)


def test_naive_timestamp_is_taken_as_utc() -> None:
    """Test a timestamp without an offset does not crash comparisons."""
    observation = observation_from_pegelonline(
        WATER_LEVEL, [_point("2026-10-23T11:00:00", 21.0)], "cm"
    )

    assert observation.observed_on == datetime(2026, 10, 23, 11, 0, tzinfo=UTC)


def test_input_order_does_not_matter() -> None:
    """Test the newest point is the newest by time, not by position."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            _point("2026-10-23T13:00:00+02:00", 30.0),
            _point("2026-10-22T13:00:00+02:00", 25.0),
            _point("2026-10-16T13:00:00+02:00", 20.0),
        ],
        "cm",
    )

    assert observation.value == 30.0
    assert observation.change_1d == 5.0
    assert observation.change_7d == 10.0


def test_trend_compares_24_hour_means() -> None:
    """Test the trend is a difference of means, not of two single readings."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            # The 24 hours ending a day before the newest reading: mean 22.
            _point("2026-10-21T20:00:00+02:00", 20.0),
            _point("2026-10-22T08:00:00+02:00", 24.0),
            # The last 24 hours: mean 40.
            _point("2026-10-22T14:00:00+02:00", 50.0),
            _point("2026-10-23T13:00:00+02:00", 30.0),
        ],
        "cm",
    )

    assert observation.value == 30.0
    assert observation.change_1d == pytest.approx(40.0 - 22.0)


def test_window_edges_belong_to_the_later_window() -> None:
    """Test a reading exactly 24 hours old is in the earlier window only."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            _point("2026-10-22T13:00:00+02:00", 10.0),  # exactly 24 h before
            _point("2026-10-23T13:00:00+02:00", 30.0),
        ],
        "cm",
    )

    assert observation.change_1d == 20.0  # 30 against 10, not against 20


@pytest.mark.parametrize("period_hours", [12.0, 12.42])
def test_tide_does_not_dominate_the_trend(period_hours: float) -> None:
    """Test a tidal swing of +-150 cm does not hide a 12 cm rise per day.

    Two single readings 24 hours apart differ by up to 63 cm just from the
    phase of the tide; the 24-hour means stay within a few cm of the truth.
    """
    start = datetime(2026, 10, 1, tzinfo=UTC)

    def level(hours: float) -> float:
        return 300 + 0.5 * hours + 150 * math.sin(2 * math.pi * hours / period_hours)

    points = [
        _point((start + timedelta(minutes=minute)).isoformat(), level(minute / 60))
        for minute in range(0, 10 * 24 * 60, 5)
    ]

    worst_mean_error = 0.0
    worst_reading_error = 0.0
    for step in range(48):
        end = len(points) - 1 - step * 6
        observation = observation_from_pegelonline(WATER_LEVEL, points[: end + 1], "cm")
        hours = end * 5 / 60
        worst_mean_error = max(worst_mean_error, abs(observation.change_1d - 12.0))
        worst_reading_error = max(
            worst_reading_error, abs(level(hours) - level(hours - 24) - 12.0)
        )

    assert worst_mean_error < 5
    if period_hours != 12.0:
        assert worst_reading_error > 40  # what two single readings would show


def test_no_trend_without_enough_history() -> None:
    """Test trends are None when the data does not reach back far enough."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            _point("2026-10-23T12:45:00+02:00", 20.0),
            _point("2026-10-23T13:00:00+02:00", 21.0),
        ],
        "cm",
    )

    assert observation.change_1d is None
    assert observation.change_7d is None
    assert observation.minimum_30d == 20.0
    assert observation.maximum_30d == 21.0


def test_extremes_cover_only_the_last_30_days() -> None:
    """Test older points do not leak into the 30-day extremes."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            _point("2026-09-01T12:00:00+02:00", 500.0),  # 52 days before
            _point("2026-10-23T13:00:00+02:00", 30.0),
        ],
        "cm",
    )

    assert observation.maximum_30d == 30.0
    assert observation.sample_count == 2


@pytest.mark.parametrize(
    "bad_value",
    [None, "n/a", "", math.nan, math.inf, -math.inf],
)
def test_unusable_values_are_skipped(bad_value: object) -> None:
    """Test null, text and non-finite values never become the reading."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            _point("2026-10-23T12:45:00+02:00", 20.0),
            _point("2026-10-23T13:00:00+02:00", bad_value),
        ],
        "cm",
    )

    assert observation.value == 20.0
    assert observation.sample_count == 1


def test_unusable_timestamps_are_skipped() -> None:
    """Test points with a missing or broken timestamp are ignored."""
    observation = observation_from_pegelonline(
        WATER_LEVEL,
        [
            {"value": 5.0},
            _point("not a time", 6.0),
            _point(None, 7.0),
            _point("2026-10-23T13:00:00+02:00", 21.0),
        ],
        "cm",
    )

    assert observation.value == 21.0
    assert observation.sample_count == 1


def test_value_may_be_a_numeric_string() -> None:
    """Test a value delivered as text is read."""
    observation = observation_from_pegelonline(
        WATER_LEVEL, [_point("2026-10-23T13:00:00+02:00", "21.5")], "cm"
    )

    assert observation.value == 21.5


def test_negative_levels_are_real() -> None:
    """Test tidal gauges below their datum are not mistaken for placeholders."""
    observation = observation_from_pegelonline(
        WATER_LEVEL, [_point("2026-10-23T13:00:00+02:00", -120.0)], "cm"
    )

    assert observation.value == -120.0


@pytest.mark.parametrize("measurements", [[], [{}], [_point(None, None)]])
def test_no_valid_measurement_gives_an_empty_observation(
    measurements: list[dict[str, object]],
) -> None:
    """Test a station without usable data yields no value but keeps its unit."""
    observation = observation_from_pegelonline(WATER_LEVEL, measurements, "cm")

    assert observation.value is None
    assert observation.observed_on is None
    assert observation.unit == "cm"
    assert observation.sample_count == 0
    assert observation.change_7d is None


# --- MNW/MHW state -----------------------------------------------------------


@pytest.mark.parametrize(
    ("uuid", "expected"),
    [
        (fixtures.AHLDEN, ("low", "low")),
        (fixtures.CELLE, ("normal", "normal")),
        (fixtures.HAMM_OW, (None, "unknown")),
        (fixtures.MELLUMPLATE, (None, "commented")),
    ],
)
def test_real_level_states(uuid: str, expected: tuple[str | None, str]) -> None:
    """Test the states captured from the live service."""
    current = fixtures.timeseries(uuid, "W")["currentMeasurement"]

    assert level_state_from_pegelonline(current) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("low", ("low", "low")),
        ("normal", ("normal", "normal")),
        ("high", ("high", "high")),
        ("unknown", (None, "unknown")),
        ("commented", (None, "commented")),
        ("out-dated", (None, "out-dated")),
        ("something new", (None, "something new")),
    ],
)
def test_level_state_vocabulary(raw: str, expected: tuple[str | None, str]) -> None:
    """Test the documented values; anything else is kept raw but not a state."""
    assert level_state_from_pegelonline({"stateMnwMhw": raw}) == expected


@pytest.mark.parametrize("current", [None, {}, {"stateMnwMhw": None}, {"stateMnwMhw": 3}, "x"])
def test_level_state_without_a_usable_value(current: object) -> None:
    """Test discharge (no state attributes) and malformed input."""
    assert level_state_from_pegelonline(current) == (None, None)  # type: ignore[arg-type]

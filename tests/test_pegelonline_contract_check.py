"""Tests for the PEGELONLINE API contract check (tools/pegelonline_contract_check.py)."""

import copy

import pytest

from tests import pegelonline_fixtures as fixtures
from tools.pegelonline_contract_check import (
    check_measurements,
    check_station_list,
    check_timeseries,
)


def _stations() -> list[dict]:
    return list(fixtures.stations_sample().values())


def _check(stations: list[dict]) -> list[str]:
    """Check with floors small enough for the sample (not the whole service)."""
    return check_station_list(stations, minimum_water_level=5, minimum_discharge=1)


def test_real_station_list_has_no_problems() -> None:
    """Test the captured stations satisfy every expectation."""
    assert _check(_stations()) == []


@pytest.mark.parametrize("response", [None, {}, [], "text"])
def test_station_list_must_be_a_non_empty_list(response: object) -> None:
    """Test a changed response shape is reported."""
    (problem,) = check_station_list(response)

    assert "non-empty list" in problem


def test_missing_station_key_is_reported() -> None:
    """Test a renamed field (the mapper reads uuid, longname, timeseries)."""
    stations = copy.deepcopy(_stations())
    for station in stations:
        station.pop("longname")

    assert any("longname" in problem for problem in _check(stations))


def test_unexpected_water_level_unit_is_reported() -> None:
    """Test a new unit the trend code cannot read."""
    stations = copy.deepcopy(_stations())
    for station in stations:
        for series in station["timeseries"]:
            if series["shortname"] == "W":
                series["unit"] = "ft"

    assert any("W/'ft'" in problem for problem in _check(stations))


def test_metres_above_a_datum_are_expected() -> None:
    """Test m+NN and m+PNP are known, not drift."""
    stations = copy.deepcopy(_stations())
    for station in stations:
        for series in station["timeseries"]:
            if series["shortname"] == "W":
                series["unit"] = "m+PNP"

    assert _check(stations) == []


def test_unexpected_discharge_unit_is_reported() -> None:
    """Test discharge in anything but m³/s."""
    stations = copy.deepcopy(_stations())
    for station in stations:
        for series in station["timeseries"]:
            if series["shortname"] == "Q":
                series["unit"] = "l/s"

    assert any("Q/'l/s'" in problem for problem in _check(stations))


def test_series_without_interval_is_reported() -> None:
    """Test the update interval field disappearing."""
    stations = copy.deepcopy(_stations())
    for station in stations:
        for series in station["timeseries"]:
            series.pop("equidistance", None)

    assert any("without an interval" in problem for problem in _check(stations))


def test_a_service_that_lost_most_stations_is_reported() -> None:
    """Test the sanity floors catch a truncated list."""
    problems = check_station_list(_stations())

    assert any("water-level series" in problem for problem in problems)
    assert any("discharge series" in problem for problem in problems)


def test_real_measurements_have_no_problems() -> None:
    """Test the captured measurements satisfy the expectations."""
    assert check_measurements("Kaub/W", fixtures.measurements(fixtures.KAUB, "W")) == []


@pytest.mark.parametrize("points", [None, {}, [], "text"])
def test_measurements_must_be_a_non_empty_list(points: object) -> None:
    """Test an empty or reshaped history."""
    (problem,) = check_measurements("x", points)

    assert "non-empty list" in problem


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ({"value": 1.0}, "unreadable timestamp"),
        ({"timestamp": "yesterday", "value": 1.0}, "unreadable timestamp"),
        ({"timestamp": "2026-10-23T13:00:00", "value": 1.0}, "without an offset"),
        ({"timestamp": "2026-10-23T13:00:00+02:00", "value": "1"}, "non-numeric"),
        ({"timestamp": "2026-10-23T13:00:00+02:00"}, "non-numeric"),
        ("point", "not an object"),
    ],
)
def test_measurement_drift_is_reported(point: object, expected: str) -> None:
    """Test each way a measurement can stop being what the mapper reads."""
    (problem,) = check_measurements("x", [point])

    assert expected in problem


@pytest.mark.parametrize(
    ("uuid", "series", "water_level"),
    [
        (fixtures.KAUB, "W", True),
        (fixtures.KAUB, "Q", False),
        (fixtures.HAMM_UW, "W", True),
        (fixtures.HAMM_OW, "W", True),
        (fixtures.MELLUMPLATE, "W", True),
    ],
)
def test_real_time_series_have_no_problems(
    uuid: str, series: str, water_level: bool
) -> None:
    """Test every captured series, including the odd states and units."""
    data = fixtures.timeseries(uuid, series)

    assert check_timeseries(f"{uuid}/{series}", data, water_level=water_level) == []


def test_unknown_state_word_is_reported() -> None:
    """Test a new word for stateMnwMhw must be handled on purpose."""
    data = fixtures.timeseries(fixtures.AHLDEN, "W")
    data["currentMeasurement"]["stateMnwMhw"] = "extreme"

    (problem,) = check_timeseries("x", data, water_level=True)

    assert "stateMnwMhw" in problem and "extreme" in problem


def test_discharge_needs_no_state() -> None:
    """Test only water levels carry the MNW/MHW state."""
    data = fixtures.timeseries(fixtures.KAUB, "Q")

    assert "stateMnwMhw" not in data["currentMeasurement"]
    assert check_timeseries("x", data, water_level=False) == []


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ([], "not an object"),
        ({"currentMeasurement": {}}, "no unit"),
        ({"unit": "cm"}, "no currentMeasurement"),
    ],
)
def test_time_series_drift_is_reported(data: object, expected: str) -> None:
    """Test the structural failures of a time series."""
    problems = check_timeseries("x", data, water_level=True)

    assert any(expected in problem for problem in problems)

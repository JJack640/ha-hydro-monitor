"""Tests for the PEGELONLINE observation fetcher."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers.pegelonline.api import (
    PegelonlineConnectionError,
    PegelonlineResponseError,
)
from custom_components.hydro_monitor.providers.pegelonline.fetcher import (
    PegelonlineObservationFetcher,
)
from tests import pegelonline_fixtures as fixtures

WATER_LEVEL = HydroMeasurementType.WATER_LEVEL
DISCHARGE = HydroMeasurementType.DISCHARGE


def _station(uuid: str = fixtures.KAUB) -> HydroStation:
    return HydroStation(
        provider="pegelonline",
        station_id=uuid,
        name="Kaub",
        measurement_types=(DISCHARGE, WATER_LEVEL),
    )


def _client(uuid: str = fixtures.KAUB, series: str = "W") -> MagicMock:
    """A client answering with the real captures of one station."""
    client = MagicMock()
    client.async_get_measurements = AsyncMock(
        return_value=fixtures.measurements(uuid, series)
    )
    client.async_get_timeseries = AsyncMock(
        return_value=fixtures.timeseries(uuid, series)
    )
    return client


def _fetcher(
    client: MagicMock,
    measurement_type: HydroMeasurementType = WATER_LEVEL,
    uuid: str = fixtures.KAUB,
) -> PegelonlineObservationFetcher:
    return PegelonlineObservationFetcher(client, _station(uuid), measurement_type)


@pytest.mark.asyncio
async def test_water_level_update() -> None:
    """Test a full update of a real gauge with an MNW/MHW state."""
    client = _client(fixtures.AHLDEN)

    observation = await _fetcher(client, uuid=fixtures.AHLDEN).async_update()

    raw = fixtures.measurements(fixtures.AHLDEN, "W")
    assert observation.measurement_type is WATER_LEVEL
    assert observation.value == raw[-1]["value"]
    assert observation.unit == "cm"
    assert isinstance(observation.observed_on, datetime)
    assert observation.observed_on.tzinfo is UTC
    assert observation.level_state == "low"
    assert observation.level_state_raw == "low"
    assert observation.level_state_error is None


@pytest.mark.asyncio
async def test_requests_use_the_stations_uuid_and_series() -> None:
    """Test which station and series are asked for."""
    client = _client()

    await _fetcher(client, WATER_LEVEL).async_update()

    client.async_get_measurements.assert_awaited_once_with(fixtures.KAUB, "W")
    client.async_get_timeseries.assert_awaited_once_with(fixtures.KAUB, "W")


@pytest.mark.asyncio
async def test_discharge_update_asks_for_series_q_and_has_no_level_state() -> None:
    """Test discharge: series Q, unit m³/s, and no water level state."""
    client = _client(series="Q")

    observation = await _fetcher(client, DISCHARGE).async_update()

    client.async_get_measurements.assert_awaited_once_with(fixtures.KAUB, "Q")
    assert observation.unit == "m³/s"
    assert observation.level_state is None
    assert observation.level_state_raw is None
    assert observation.level_state_error is None


@pytest.mark.asyncio
async def test_unit_comes_from_the_series_not_from_an_assumption() -> None:
    """Test a gauge in metres above NN keeps that unit."""
    client = _client(fixtures.HAMM_UW)

    observation = await _fetcher(client, uuid=fixtures.HAMM_UW).async_update()

    assert observation.unit == "m+NN"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("uuid", "raw"), [(fixtures.HAMM_OW, "unknown"), (fixtures.MELLUMPLATE, "commented")]
)
async def test_unusable_state_is_no_state_but_not_an_error(uuid: str, raw: str) -> None:
    """Test unknown/commented give no state, keep the raw word, and no error."""
    client = _client(uuid)

    observation = await _fetcher(client, uuid=uuid).async_update()

    assert observation.level_state is None
    assert observation.level_state_raw == raw
    assert observation.level_state_error is None


@pytest.mark.asyncio
async def test_measurement_failure_fails_the_update() -> None:
    """Test no measurements, no reading: the coordinator reports the outage."""
    client = _client()
    client.async_get_measurements.side_effect = PegelonlineConnectionError("down")

    with pytest.raises(PegelonlineConnectionError):
        await _fetcher(client).async_update()


@pytest.mark.asyncio
async def test_series_failure_on_the_first_update_fails_it() -> None:
    """Test without a known unit there is nothing to report the value in."""
    client = _client()
    client.async_get_timeseries.side_effect = PegelonlineConnectionError("down")

    with pytest.raises(PegelonlineConnectionError):
        await _fetcher(client).async_update()


@pytest.mark.asyncio
async def test_series_failure_later_keeps_the_value_and_records_the_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a failing second request does not take the reading down with it."""
    client = _client()
    fetcher = _fetcher(client)
    first = await fetcher.async_update()

    client.async_get_timeseries.side_effect = PegelonlineConnectionError("flaky")
    second = await fetcher.async_update()

    assert second.value == first.value
    assert second.unit == "cm"
    assert second.level_state is None
    assert second.level_state_error == "flaky"
    assert "Could not fetch the PEGELONLINE time series" in caplog.text


@pytest.mark.asyncio
async def test_series_failure_does_not_set_a_level_error_for_discharge() -> None:
    """Test discharge has no state, so a failure there records none."""
    client = _client(series="Q")
    fetcher = _fetcher(client, DISCHARGE)
    await fetcher.async_update()

    client.async_get_timeseries.side_effect = PegelonlineConnectionError("flaky")
    observation = await fetcher.async_update()

    assert observation.value is not None
    assert observation.level_state_error is None


@pytest.mark.asyncio
async def test_unit_is_remembered_across_updates() -> None:
    """Test the unit survives a response that lacks it."""
    client = _client()
    fetcher = _fetcher(client)
    await fetcher.async_update()

    client.async_get_timeseries.return_value = {"shortname": "W"}  # no unit
    observation = await fetcher.async_update()

    assert observation.unit == "cm"


@pytest.mark.asyncio
async def test_malformed_series_response_is_handled_like_a_failure() -> None:
    """Test a response error from the series request on a first update."""
    client = _client()
    client.async_get_timeseries.side_effect = PegelonlineResponseError("bad")

    with pytest.raises(PegelonlineResponseError):
        await _fetcher(client).async_update()


@pytest.mark.asyncio
async def test_station_without_measurements_gives_an_empty_observation() -> None:
    """Test an empty history yields no value rather than an error."""
    client = _client()
    client.async_get_measurements.return_value = []

    observation = await _fetcher(client).async_update()

    assert observation.value is None
    assert observation.unit == "cm"
    assert observation.observed_on is None

"""Tests for the provider registry and the NIWIS provider definition."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers import (
    PROVIDERS,
    get_provider,
    providers_for,
)
from custom_components.hydro_monitor.providers.base import ProviderError
from custom_components.hydro_monitor.providers.niwis.api import (
    NiwisConnectionError,
    NiwisError,
    NiwisResponseError,
)
from custom_components.hydro_monitor.providers.niwis.catalog import NiwisCatalog
from custom_components.hydro_monitor.providers.niwis.fetcher import (
    NiwisObservationFetcher,
)
from custom_components.hydro_monitor.providers.niwis.provider import NIWIS_PROVIDER
from custom_components.hydro_monitor.providers.pegelonline.provider import (
    PEGELONLINE_PROVIDER,
)


def test_providers_are_registered() -> None:
    """Test the registry holds each provider under its stored id."""
    assert get_provider("niwis") is NIWIS_PROVIDER
    assert get_provider("pegelonline") is PEGELONLINE_PROVIDER
    assert set(PROVIDERS) == {"niwis", "pegelonline"}


def test_provider_id_is_the_stable_stored_value() -> None:
    """Test the id that prefixes every unique id never changes."""
    assert NIWIS_PROVIDER.id == "niwis"


def test_unknown_provider_raises_key_error() -> None:
    """Test a config entry naming an unknown provider is detectable."""
    with pytest.raises(KeyError):
        get_provider("does_not_exist")


@pytest.mark.parametrize(
    ("measurement_type", "expected"),
    [
        (HydroMeasurementType.DISCHARGE, [NIWIS_PROVIDER, PEGELONLINE_PROVIDER]),
        (HydroMeasurementType.WATER_LEVEL, [NIWIS_PROVIDER, PEGELONLINE_PROVIDER]),
        (HydroMeasurementType.GROUNDWATER_LEVEL, [NIWIS_PROVIDER]),
        (HydroMeasurementType.SPRING_DISCHARGE, [NIWIS_PROVIDER]),
    ],
)
def test_providers_for_each_measurement_type(
    measurement_type: HydroMeasurementType,
    expected: list,
) -> None:
    """Test which providers are asked for which measurement type.

    NIWIS serves all four; PEGELONLINE only the two surface-water ones.
    """
    assert providers_for(measurement_type) == expected


def test_niwis_definition_keeps_todays_behaviour() -> None:
    """Test the values that existing NIWIS entries depend on."""
    assert NIWIS_PROVIDER.name == "NIWIS"
    assert NIWIS_PROVIDER.update_interval == timedelta(hours=6)
    # None = every sensor the integration defines, i.e. no filtering.
    assert NIWIS_PROVIDER.observation_sensor_keys is None
    assert NIWIS_PROVIDER.create_catalog is NiwisCatalog


@pytest.mark.parametrize(
    "error",
    [NiwisError, NiwisConnectionError, NiwisResponseError],
)
def test_niwis_errors_are_provider_errors(error: type[Exception]) -> None:
    """Test generic code can catch NIWIS failures as ProviderError."""
    assert issubclass(error, ProviderError)


def test_create_fetcher_builds_a_niwis_fetcher() -> None:
    """Test the NIWIS provider creates the NIWIS fetcher for an entry."""
    station = HydroStation(
        provider="niwis",
        station_id="DESM_DEBY16607001",
        name="Inkofen",
        measurement_types=(HydroMeasurementType.DISCHARGE,),
    )

    with patch(
        "custom_components.hydro_monitor.providers.niwis.provider.async_get_clientsession"
    ):
        fetcher = NIWIS_PROVIDER.create_fetcher(
            MagicMock(), station, HydroMeasurementType.DISCHARGE
        )

    assert isinstance(fetcher, NiwisObservationFetcher)
    assert fetcher.station is station
    assert fetcher.measurement_type is HydroMeasurementType.DISCHARGE


@pytest.mark.asyncio
async def test_get_station_maps_the_niwis_station() -> None:
    """Test a station is loaded through the NIWIS client and mapper."""
    raw = {"messstelleNr": "DESM_DEBY16607001", "name": "Inkofen"}
    expected = HydroStation(
        provider="niwis",
        station_id="DESM_DEBY16607001",
        name="Inkofen",
        measurement_types=(),
    )

    with (
        patch(
            "custom_components.hydro_monitor.providers.niwis.provider.async_get_clientsession"
        ),
        patch(
            "custom_components.hydro_monitor.providers.niwis.provider.NiwisClient"
        ) as client,
        patch(
            "custom_components.hydro_monitor.providers.niwis.provider.station_from_niwis",
            return_value=expected,
        ) as mapper,
    ):
        client.return_value.async_get_station = MagicMock(
            side_effect=lambda station_id: _awaitable(raw)
        )

        station = await NIWIS_PROVIDER.get_station(MagicMock(), "DESM_DEBY16607001")

    assert station is expected
    mapper.assert_called_once_with(raw)


async def _awaitable(value: object) -> object:
    return value


# --- PEGELONLINE -------------------------------------------------------------


def test_pegelonline_definition() -> None:
    """Test the values the PEGELONLINE entries are built on."""
    assert PEGELONLINE_PROVIDER.id == "pegelonline"
    assert PEGELONLINE_PROVIDER.name == "PEGELONLINE"
    assert PEGELONLINE_PROVIDER.measurement_types == frozenset(
        {HydroMeasurementType.WATER_LEVEL, HydroMeasurementType.DISCHARGE}
    )
    assert PEGELONLINE_PROVIDER.update_interval == timedelta(minutes=30)


def test_pegelonline_sensor_keys_are_real_sensors() -> None:
    """Test a typo in the key list cannot silently drop a sensor."""
    from custom_components.hydro_monitor.sensor import SENSOR_DESCRIPTIONS

    all_keys = {description.key for description in SENSOR_DESCRIPTIONS}

    assert PEGELONLINE_PROVIDER.observation_sensor_keys is not None
    assert PEGELONLINE_PROVIDER.observation_sensor_keys <= all_keys


def test_pegelonline_sensors_are_only_what_a_raw_series_can_fill() -> None:
    """Test no NIWIS classification or reference statistic is offered."""
    keys = PEGELONLINE_PROVIDER.observation_sensor_keys

    assert keys == {
        "value",
        "change_1d",
        "change_7d",
        "trend_state",
        "level_state",
        "maximum_30d",
        "minimum_30d",
        "last_measurement",
        "measurement_age",
    }


def test_pegelonline_errors_are_provider_errors() -> None:
    """Test generic code can catch PEGELONLINE failures as ProviderError."""
    from custom_components.hydro_monitor.providers.pegelonline.api import (
        PegelonlineConnectionError,
        PegelonlineError,
        PegelonlineResponseError,
    )

    for error in (PegelonlineError, PegelonlineConnectionError, PegelonlineResponseError):
        assert issubclass(error, ProviderError)


def test_create_catalog_is_the_pegelonline_catalog() -> None:
    """Test the config flow gets this provider's catalog."""
    from custom_components.hydro_monitor.providers.pegelonline.catalog import (
        PegelonlineCatalog,
    )

    assert PEGELONLINE_PROVIDER.create_catalog is PegelonlineCatalog


def test_create_pegelonline_fetcher() -> None:
    """Test the provider creates its fetcher for an entry."""
    from custom_components.hydro_monitor.providers.pegelonline.fetcher import (
        PegelonlineObservationFetcher,
    )

    station = HydroStation(
        provider="pegelonline",
        station_id="u1",
        name="Kaub",
        measurement_types=(HydroMeasurementType.WATER_LEVEL,),
    )

    with patch(
        "custom_components.hydro_monitor.providers.pegelonline.provider.async_get_clientsession"
    ):
        fetcher = PEGELONLINE_PROVIDER.create_fetcher(
            MagicMock(), station, HydroMeasurementType.WATER_LEVEL
        )

    assert isinstance(fetcher, PegelonlineObservationFetcher)
    assert fetcher.station is station


@pytest.mark.asyncio
async def test_pegelonline_get_station_maps_the_response() -> None:
    """Test a station is loaded by uuid through the client and mapper."""
    from tests import pegelonline_fixtures as fixtures

    raw = fixtures.station(fixtures.KAUB)

    with (
        patch(
            "custom_components.hydro_monitor.providers.pegelonline.provider.async_get_clientsession"
        ),
        patch(
            "custom_components.hydro_monitor.providers.pegelonline.provider.PegelonlineClient"
        ) as client,
    ):
        client.return_value.async_get_station = MagicMock(
            side_effect=lambda station_id: _awaitable(raw)
        )

        station = await PEGELONLINE_PROVIDER.get_station(MagicMock(), fixtures.KAUB)

    assert station.provider == "pegelonline"
    assert station.station_id == fixtures.KAUB
    assert station.name == "Kaub"
    client.return_value.async_get_station.assert_called_once_with(fixtures.KAUB)

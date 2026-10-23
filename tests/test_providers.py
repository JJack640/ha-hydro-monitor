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


def test_niwis_is_registered() -> None:
    """Test the registry holds NIWIS under the id stored in config entries."""
    assert get_provider("niwis") is NIWIS_PROVIDER
    assert set(PROVIDERS) == {"niwis"}


def test_provider_id_is_the_stable_stored_value() -> None:
    """Test the id that prefixes every unique id never changes."""
    assert NIWIS_PROVIDER.id == "niwis"


def test_unknown_provider_raises_key_error() -> None:
    """Test a config entry naming an unknown provider is detectable."""
    with pytest.raises(KeyError):
        get_provider("does_not_exist")


@pytest.mark.parametrize("measurement_type", list(HydroMeasurementType))
def test_niwis_serves_every_measurement_type(
    measurement_type: HydroMeasurementType,
) -> None:
    """Test NIWIS is offered for all four measurement types."""
    assert providers_for(measurement_type) == [NIWIS_PROVIDER]


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

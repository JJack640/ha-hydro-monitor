"""Tests for the Hydro Monitor coordinator."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers.niwis.api import NiwisConnectionError
from custom_components.hydro_monitor.providers.niwis.const import (
    DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC,
    DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC,
    DERIVED_ENDPOINT_LOW_WATER_CLASS,
)


def _station() -> HydroStation:
    """Create a representative station for coordinator tests."""
    return HydroStation(
        provider="niwis",
        station_id="DESM_DEBY16607001",
        name="Inkofen",
        measurement_types=(HydroMeasurementType.DISCHARGE,),
    )


def _series() -> list[dict[str, object]]:
    """Create a minimal single-point NIWIS series."""
    return [{"datum": "2026-07-20", "messwert": "10,5", "einheit": "m³/s", "flag": "A"}]


def _classification_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS classification response."""
    response: dict[str, object] = {
        "einzelwert": "extrem niedrig",
        "einheit": None,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _official_development_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS 'Entwicklung letzte 7 Tage' response."""
    response: dict[str, object] = {
        "einzelwert": "gleichbleibend",
        "einheit": None,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _classification_labels() -> list[str]:
    """Return the official 4-value low-water classification scheme."""
    return ["extrem niedrig", "sehr niedrig", "niedrig", "kein Niedrigwasser"]


def _static_boundaries_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS static-boundaries response."""
    response: dict[str, object] = {
        "schwellenwerte": [20.3, 25.0, 33.4],
        "klassifikationen": _classification_labels(),
        "einheit": "m³/s",
        "beidseitigOffeneSchwellenwerte": True,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _dynamic_boundaries_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS dynamic-boundaries response."""
    response: dict[str, object] = {
        "schwellenwerteProTag": [[24.3, 26.0, 33.6]] * 366,
        "klassifikationen": _classification_labels(),
        "einheit": "m³/s",
        "beidseitigOffeneSchwellenwerte": True,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _routed_client(
    *,
    classification: object = None,
    official_development: object = None,
    static: object = None,
    dynamic: object = None,
) -> AsyncMock:
    """Build a client whose async_get_derived_result routes by quantity.

    DERIVED_ENDPOINT_LOW_WATER_CLASS is shared by two different quantities
    (low-water classification and, since Sprint 3, the official 7-day
    development) — routed by whether "Entwicklung" appears in the
    requested abgeleiteteGroesse, which holds regardless of measurement
    type. The two boundary endpoints are still routed by endpoint alone
    since each only ever serves one quantity family in this codebase.
    """
    client = AsyncMock()
    client.async_get_series.return_value = _series()

    by_endpoint = {
        DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC: (
            static or _static_boundaries_response()
        ),
        DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC: (
            dynamic or _dynamic_boundaries_response()
        ),
    }

    async def _async_get_derived_result(endpoint: str, params: dict[str, str]) -> object:
        if endpoint == DERIVED_ENDPOINT_LOW_WATER_CLASS:
            if "Entwicklung" in params["abgeleiteteGroesse"]:
                result = official_development or _official_development_response()
            else:
                result = classification or _classification_response()
        else:
            result = by_endpoint[endpoint]

        if isinstance(result, Exception):
            raise result
        return result

    client.async_get_derived_result.side_effect = _async_get_derived_result
    return client


def _coordinator(
    client: AsyncMock,
    measurement_type: HydroMeasurementType = HydroMeasurementType.DISCHARGE,
) -> HydroMonitorCoordinator:
    """Build a coordinator instance without running __init__."""
    coordinator = HydroMonitorCoordinator.__new__(HydroMonitorCoordinator)
    coordinator.station = _station()
    coordinator.measurement_type = measurement_type
    coordinator.client = client
    coordinator._dynamic_boundaries = None
    coordinator._dynamic_boundaries_date = None
    return coordinator


@pytest.mark.asyncio
async def test_update_merges_low_water_class_on_success() -> None:
    """Test that a successful classification call is merged into the observation."""
    observation = await _coordinator(_routed_client())._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.low_water_class == "extremely_low"
    assert observation.low_water_class_raw == "extrem niedrig"
    assert observation.low_water_class_error is None


@pytest.mark.asyncio
async def test_update_raises_update_failed_on_primary_series_failure() -> None:
    """Test that a failed primary series fetch fails the whole update."""
    client = _routed_client()
    client.async_get_series.side_effect = NiwisConnectionError("boom")

    with pytest.raises(UpdateFailed):
        await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_not_called()


@pytest.mark.asyncio
async def test_update_survives_classification_failure() -> None:
    """Test that a failed classification call does not fail the whole update."""
    client = _routed_client(classification=NiwisConnectionError("classification down"))

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.low_water_class is None
    assert observation.low_water_class_error == "classification down"
    # Boundaries are fetched independently of the classification failure.
    assert observation.boundaries is not None
    assert observation.boundaries.static_thresholds == pytest.approx((20.3, 25.0, 33.4))


@pytest.mark.asyncio
async def test_update_requests_expected_classification_parameters() -> None:
    """Test the exact endpoint and params sent for the classification request."""
    client = _routed_client()

    await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_LOW_WATER_CLASS,
        {
            "abgeleiteteGroesse": "Abfluss Niedrigwasserklasse aktueller Tag",
            "messstelleNr": "DESM_DEBY16607001",
            "jahresdefinition": "KALENDERJAHR",
            "startJahr": "1991",
            "endJahr": "2020",
        },
    )


@pytest.mark.asyncio
async def test_update_merges_static_and_dynamic_boundaries_on_success() -> None:
    """Test that successful static and dynamic boundary fetches are merged."""
    observation = await _coordinator(_routed_client())._async_update_data()

    boundaries = observation.boundaries
    assert boundaries is not None
    assert boundaries.classification_labels == (
        "extremely_low",
        "very_low",
        "low",
        "no_low_water",
    )
    assert boundaries.static_thresholds == pytest.approx((20.3, 25.0, 33.4))
    assert boundaries.static_unit == "m³/s"
    assert boundaries.static_error is None
    assert boundaries.dynamic_thresholds == pytest.approx((24.3, 26.0, 33.6))
    assert boundaries.dynamic_unit == "m³/s"
    assert boundaries.dynamic_error is None
    assert boundaries.dynamic_reference_date == date.today()


@pytest.mark.asyncio
async def test_update_survives_static_boundary_failure() -> None:
    """Test that a failed static-boundary fetch does not fail the whole update."""
    client = _routed_client(static=NiwisConnectionError("static down"))

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.boundaries is not None
    assert observation.boundaries.static_thresholds is None
    assert observation.boundaries.static_error == "static down"
    # Dynamic boundaries are unaffected by the static failure.
    assert observation.boundaries.dynamic_thresholds is not None


@pytest.mark.asyncio
async def test_update_survives_dynamic_boundary_failure() -> None:
    """Test that a failed dynamic-boundary fetch does not fail the whole update."""
    client = _routed_client(dynamic=NiwisConnectionError("dynamic down"))

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.boundaries is not None
    assert observation.boundaries.dynamic_thresholds is None
    assert observation.boundaries.dynamic_error == "dynamic down"
    # Static boundaries are unaffected by the dynamic failure.
    assert observation.boundaries.static_thresholds is not None


@pytest.mark.asyncio
async def test_dynamic_boundary_failure_is_not_cached() -> None:
    """Test that a failed dynamic fetch is retried on the next update."""
    client = _routed_client(dynamic=NiwisConnectionError("dynamic down"))
    coordinator = _coordinator(client)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    dynamic_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC
    ]
    assert len(dynamic_calls) == 2


@pytest.mark.asyncio
async def test_dynamic_boundaries_are_cached_within_the_same_day() -> None:
    """Test that a second same-day update reuses the cached dynamic boundaries."""
    client = _routed_client()
    coordinator = _coordinator(client)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    dynamic_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC
    ]
    assert len(dynamic_calls) == 1


@pytest.mark.asyncio
async def test_dynamic_boundaries_refetch_after_day_rollover() -> None:
    """Test that a calendar-day rollover triggers a dynamic-boundary refetch."""
    client = _routed_client()
    coordinator = _coordinator(client)

    with patch(
        "custom_components.hydro_monitor.coordinator.date"
    ) as mock_date:
        mock_date.today.return_value = date(2026, 1, 1)
        await coordinator._async_update_data()

        mock_date.today.return_value = date(2026, 1, 2)
        await coordinator._async_update_data()

    dynamic_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC
    ]
    assert len(dynamic_calls) == 2


@pytest.mark.asyncio
async def test_update_requests_expected_static_boundary_parameters() -> None:
    """Test the exact endpoint and params sent for the static-boundary request."""
    client = _routed_client()

    await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC,
        {
            "abgeleiteteGroesse": "Abfluss Klassifikation mit statischen Grenzwerten",
            "messstelleNr": "DESM_DEBY16607001",
            "jahresdefinition": "KALENDERJAHR",
            "startJahr": "1991",
            "endJahr": "2020",
        },
    )


@pytest.mark.asyncio
async def test_update_requests_expected_dynamic_boundary_parameters() -> None:
    """Test the exact endpoint and params sent for the dynamic-boundary request."""
    client = _routed_client()

    await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC,
        {
            "abgeleiteteGroesse": "Abfluss Klassifikation mit variablen Grenzwerten",
            "messstelleNr": "DESM_DEBY16607001",
            "jahresdefinition": "KALENDERJAHR",
            "startJahr": "1991",
            "endJahr": "2020",
        },
    )


@pytest.mark.asyncio
async def test_update_merges_official_development_7d_on_success() -> None:
    """Test that a successful development-7d call is merged into the observation."""
    observation = await _coordinator(_routed_client())._async_update_data()

    assert observation.official_development_7d == "gleichbleibend"
    assert observation.official_development_7d_raw == "gleichbleibend"
    assert observation.official_development_7d_error is None


@pytest.mark.asyncio
async def test_update_survives_official_development_7d_failure() -> None:
    """Test that a failed development-7d call does not fail the whole update."""
    client = _routed_client(
        official_development=NiwisConnectionError("development down")
    )

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.official_development_7d is None
    assert observation.official_development_7d_error == "development down"
    # Low-water class is unaffected by the development-7d failure.
    assert observation.low_water_class == "extremely_low"


@pytest.mark.asyncio
async def test_update_requests_expected_official_development_7d_parameters() -> None:
    """Test that no reference-period params are sent (benoetigtReferenzzeitraum=false)."""
    client = _routed_client()

    await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_LOW_WATER_CLASS,
        {
            "abgeleiteteGroesse": "Abfluss Entwicklung letzte 7 Tage",
            "messstelleNr": "DESM_DEBY16607001",
        },
    )


@pytest.mark.parametrize(
    "measurement_type",
    [HydroMeasurementType.GROUNDWATER_LEVEL, HydroMeasurementType.SPRING_DISCHARGE],
)
@pytest.mark.asyncio
async def test_official_development_7d_not_fetched_for_unsupported_types(
    measurement_type: HydroMeasurementType,
) -> None:
    """Test that groundwater/spring-discharge coordinators skip this quantity.

    No catalog entry exists for these measurement types (only discharge and
    water_level support "Entwicklung letzte 7 Tage"), so the fetch must be
    skipped entirely rather than attempted and failing on a KeyError.
    """
    client = _routed_client()

    observation = await _coordinator(client, measurement_type)._async_update_data()

    assert observation.official_development_7d is None
    assert observation.official_development_7d_error is None

    for call in client.async_get_derived_result.await_args_list:
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_CLASS:
            assert "Entwicklung" not in call.args[1]["abgeleiteteGroesse"]

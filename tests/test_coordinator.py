"""Tests for the Hydro Monitor coordinator."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers.niwis.api import NiwisConnectionError
from custom_components.hydro_monitor.providers.niwis.const import (
    DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
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


def _decile_labels() -> list[str]:
    """Return the official 10-value decile classification scheme."""
    return [
        "0-10%", "10-20%", "20-30%", "30-40%", "40-50%",
        "50-60%", "60-70%", "70-80%", "80-90%", "90-100%",
    ]


def _decile_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS deciles response."""
    response: dict[str, object] = {
        "schwellenwerteProTag": [list(range(11))] * 366,
        "klassifikationen": _decile_labels(),
        "einheit": "m³/s",
        "beidseitigOffeneSchwellenwerte": False,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _historical_statistic_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS berechneEinzelwertNummer response."""
    response: dict[str, object] = {
        "einzelwert": 42.0,
        "einheit": "m³/s",
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
    deciles: object = None,
    historical_statistics: dict[str, object] | None = None,
) -> AsyncMock:
    """Build a client whose async_get_derived_result routes by quantity.

    DERIVED_ENDPOINT_LOW_WATER_CLASS is shared by two different quantities
    (low-water classification and, since Sprint 3, the official 7-day
    development) — routed by whether "Entwicklung" appears in the
    requested abgeleiteteGroesse, which holds regardless of measurement
    type. DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC is likewise shared
    by the low-water dynamic boundaries and, since Sprint 5, deciles —
    routed by whether "Dezile" appears in the requested abgeleiteteGroesse.
    DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC still only ever serves one
    quantity family, so it's routed by endpoint alone.
    DERIVED_ENDPOINT_HISTORICAL_STATISTICS (Sprint 4) is routed by the
    exact abgeleiteteGroesse value (e.g. "MQ", "MW") via the
    historical_statistics override dict, keyed the same way.
    """
    client = AsyncMock()
    client.async_get_series.return_value = _series()

    historical_statistics = historical_statistics or {}

    async def _async_get_derived_result(endpoint: str, params: dict[str, str]) -> object:
        if endpoint == DERIVED_ENDPOINT_LOW_WATER_CLASS:
            if "Entwicklung" in params["abgeleiteteGroesse"]:
                result = official_development or _official_development_response()
            else:
                result = classification or _classification_response()
        elif endpoint == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC:
            if "Dezile" in params["abgeleiteteGroesse"]:
                result = deciles or _decile_response()
            else:
                result = dynamic or _dynamic_boundaries_response()
        elif endpoint == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC:
            result = static or _static_boundaries_response()
        elif endpoint == DERIVED_ENDPOINT_HISTORICAL_STATISTICS:
            result = historical_statistics.get(
                params["abgeleiteteGroesse"], _historical_statistic_response()
            )
        else:
            raise AssertionError(f"unrouted endpoint: {endpoint}")

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
    coordinator._deciles = None
    coordinator._deciles_date = None
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
        and "Dezile" not in call.args[1]["abgeleiteteGroesse"]
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
        and "Dezile" not in call.args[1]["abgeleiteteGroesse"]
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
        and "Dezile" not in call.args[1]["abgeleiteteGroesse"]
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


@pytest.mark.asyncio
async def test_update_merges_historical_statistics_on_success_for_discharge() -> None:
    """Test that MQ/MNQ/NM7Q/NM30Q are populated for discharge, MW/MNW stay None."""
    observation = await _coordinator(_routed_client())._async_update_data()

    assert observation.mq is not None
    assert observation.mq.value == pytest.approx(42.0)
    assert observation.mq.unit == "m³/s"
    assert observation.mq.error is None
    assert observation.mnq is not None
    assert observation.nm7q is not None
    assert observation.nm30q is not None

    assert observation.mw is None
    assert observation.mnw is None


@pytest.mark.asyncio
async def test_update_merges_historical_statistics_on_success_for_water_level() -> None:
    """Test that MW/MNW are populated for water_level, the Q-quantities stay None."""
    observation = await _coordinator(
        _routed_client(), HydroMeasurementType.WATER_LEVEL
    )._async_update_data()

    assert observation.mw is not None
    assert observation.mw.value == pytest.approx(42.0)
    assert observation.mnw is not None

    assert observation.mq is None
    assert observation.mnq is None
    assert observation.nm7q is None
    assert observation.nm30q is None


@pytest.mark.asyncio
async def test_update_survives_historical_statistic_failure() -> None:
    """Test that a failed MQ fetch does not fail the whole update or block others."""
    client = _routed_client(
        historical_statistics={"MQ": NiwisConnectionError("mq down")}
    )

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.mq is not None
    assert observation.mq.value is None
    assert observation.mq.error == "mq down"
    # Other historical statistics are unaffected by the MQ failure.
    assert observation.mnq is not None
    assert observation.mnq.value == pytest.approx(42.0)


@pytest.mark.parametrize("quantity", ["MQ", "MNQ", "MW", "MNW"])
@pytest.mark.asyncio
async def test_update_requests_expected_reference_period_statistic_parameters(
    quantity: str,
) -> None:
    """Test that MQ/MNQ/MW/MNW reuse the reference-period params, no interval."""
    measurement_type = (
        HydroMeasurementType.DISCHARGE
        if quantity in ("MQ", "MNQ")
        else HydroMeasurementType.WATER_LEVEL
    )
    client = _routed_client()

    await _coordinator(client, measurement_type)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
        {
            "abgeleiteteGroesse": quantity,
            "messstelleNr": "DESM_DEBY16607001",
            "jahresdefinition": "KALENDERJAHR",
            "startJahr": "1991",
            "endJahr": "2020",
        },
    )


@pytest.mark.asyncio
async def test_update_requests_expected_nm7q_interval_parameters() -> None:
    """Test that NM7Q uses the trailing 30-day analysis interval.

    Live-verified against the real API: a bare 7-day interval makes NIWIS
    return hatZuvieleFehlwerte=true for NM7Q; a 30-day interval succeeds.
    """
    client = _routed_client()

    with patch("custom_components.hydro_monitor.coordinator.date") as mock_date:
        mock_date.today.return_value = date(2026, 7, 22)
        await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
        {
            "abgeleiteteGroesse": "NM7Q",
            "messstelleNr": "DESM_DEBY16607001",
            "von": "2026-06-22",
            "bis": "2026-07-22",
        },
    )


@pytest.mark.asyncio
async def test_update_requests_expected_nm30q_interval_parameters() -> None:
    """Test that NM30Q uses the same trailing 30-day analysis interval as NM7Q."""
    client = _routed_client()

    with patch("custom_components.hydro_monitor.coordinator.date") as mock_date:
        mock_date.today.return_value = date(2026, 7, 22)
        await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
        {
            "abgeleiteteGroesse": "NM30Q",
            "messstelleNr": "DESM_DEBY16607001",
            "von": "2026-06-22",
            "bis": "2026-07-22",
        },
    )


@pytest.mark.parametrize(
    "measurement_type",
    [HydroMeasurementType.GROUNDWATER_LEVEL, HydroMeasurementType.SPRING_DISCHARGE],
)
@pytest.mark.asyncio
async def test_historical_statistics_not_fetched_for_unsupported_types(
    measurement_type: HydroMeasurementType,
) -> None:
    """Test that groundwater/spring-discharge coordinators skip this endpoint.

    No catalog entry exists at all for these measurement types in the
    berechneEinzelwertNummer endpoint family.
    """
    client = _routed_client()

    observation = await _coordinator(client, measurement_type)._async_update_data()

    assert observation.mq is None
    assert observation.mnq is None
    assert observation.nm7q is None
    assert observation.nm30q is None
    assert observation.mw is None
    assert observation.mnw is None

    for call in client.async_get_derived_result.await_args_list:
        assert call.args[0] != DERIVED_ENDPOINT_HISTORICAL_STATISTICS


@pytest.mark.asyncio
async def test_update_merges_deciles_on_success() -> None:
    """Test that a successful deciles fetch is merged into the observation."""
    observation = await _coordinator(_routed_client())._async_update_data()

    deciles = observation.deciles
    assert deciles is not None
    assert deciles.classification_labels == tuple(_decile_labels())
    assert deciles.thresholds == pytest.approx(tuple(range(11)))
    assert deciles.unit == "m³/s"
    assert deciles.error is None


@pytest.mark.asyncio
async def test_update_survives_deciles_failure() -> None:
    """Test that a failed deciles fetch does not fail the whole update."""
    client = _routed_client(deciles=NiwisConnectionError("deciles down"))

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.deciles is not None
    assert observation.deciles.thresholds is None
    assert observation.deciles.error == "deciles down"
    # Low-water boundaries are unaffected by the deciles failure.
    assert observation.boundaries.dynamic_thresholds is not None


@pytest.mark.asyncio
async def test_deciles_failure_is_not_cached() -> None:
    """Test that a failed deciles fetch is retried on the next update."""
    client = _routed_client(deciles=NiwisConnectionError("deciles down"))
    coordinator = _coordinator(client)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    decile_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC
        and "Dezile" in call.args[1]["abgeleiteteGroesse"]
    ]
    assert len(decile_calls) == 2


@pytest.mark.asyncio
async def test_deciles_are_cached_within_the_same_day() -> None:
    """Test that a second same-day update reuses the cached deciles."""
    client = _routed_client()
    coordinator = _coordinator(client)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    decile_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC
        and "Dezile" in call.args[1]["abgeleiteteGroesse"]
    ]
    assert len(decile_calls) == 1


@pytest.mark.asyncio
async def test_deciles_refetch_after_day_rollover() -> None:
    """Test that a calendar-day rollover triggers a deciles refetch."""
    client = _routed_client()
    coordinator = _coordinator(client)

    with patch("custom_components.hydro_monitor.coordinator.date") as mock_date:
        mock_date.today.return_value = date(2026, 1, 1)
        await coordinator._async_update_data()

        mock_date.today.return_value = date(2026, 1, 2)
        await coordinator._async_update_data()

    decile_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC
        and "Dezile" in call.args[1]["abgeleiteteGroesse"]
    ]
    assert len(decile_calls) == 2


@pytest.mark.asyncio
async def test_update_requests_expected_deciles_parameters() -> None:
    """Test the exact endpoint and params sent for the deciles request."""
    client = _routed_client()

    await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC,
        {
            "abgeleiteteGroesse": "Abfluss Dezile tageweise",
            "messstelleNr": "DESM_DEBY16607001",
            "jahresdefinition": "KALENDERJAHR",
            "startJahr": "1991",
            "endJahr": "2020",
        },
    )


@pytest.mark.parametrize(
    "measurement_type",
    [HydroMeasurementType.GROUNDWATER_LEVEL, HydroMeasurementType.SPRING_DISCHARGE],
)
@pytest.mark.asyncio
async def test_deciles_not_fetched_for_unsupported_types(
    measurement_type: HydroMeasurementType,
) -> None:
    """Test that groundwater/spring-discharge coordinators skip deciles.

    No catalog entry exists at all for these measurement types.
    """
    client = _routed_client()

    observation = await _coordinator(client, measurement_type)._async_update_data()

    assert observation.deciles is not None
    assert observation.deciles.thresholds is None
    assert observation.deciles.classification_labels is None

    for call in client.async_get_derived_result.await_args_list:
        if call.args[0] == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC:
            assert "Dezile" not in call.args[1]["abgeleiteteGroesse"]

"""Tests for the Hydro Monitor coordinator."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hydro_monitor.coordinator import HydroMonitorCoordinator
from custom_components.hydro_monitor.models import HydroMeasurementType, HydroStation
from custom_components.hydro_monitor.providers.niwis.api import NiwisConnectionError
from custom_components.hydro_monitor.providers.niwis.const import (
    CALENDAR_DAY_STATISTIC_NIWIS_NAMES,
    DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS,
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


def _dated_extreme_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS 'mit Datum' response (NM7Q/NM30Q mit Datum)."""
    response: dict[str, object] = {
        "einzelwert": "15.26 (15.07.2026-21.07.2026)",
        "einheit": None,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _below_glw_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS 'unter GlW' response."""
    response: dict[str, object] = {
        "einzelwert": "unterhalb",
        "einheit": None,
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _calendar_day_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS berechneZeitreihenErgebnisNummer 366-row response."""
    response: dict[str, object] = {
        "werte": [42.0] * 366,
        "einheit": "m³/s",
        "hatZuvieleFehlwerte": False,
        "fehlermeldung": None,
    }
    response.update(overrides)
    return response


def _depth_below_ground_response(**overrides: object) -> dict[str, object]:
    """Create a representative NIWIS interval berechneZeitreihenErgebnisNummer response."""
    response: dict[str, object] = {
        "startDatum": "2026-07-08",
        "werte": [12.3, 12.4, 12.5],
        "einheit": "m",
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
    dated_extremes: dict[str, object] | None = None,
    below_glw: object = None,
    calendar_day_results: dict[str, object] | None = None,
) -> AsyncMock:
    """Build a client whose async_get_derived_result routes by quantity.

    DERIVED_ENDPOINT_LOW_WATER_CLASS is shared by four different
    quantities — low-water classification, the official 7-day
    development (Sprint 3), NM7Q/NM30Q "mit Datum" and "unter GlW"
    (Sprint 7) — routed by checking the requested abgeleiteteGroesse for
    "mit Datum", an exact "unter GlW" match, then "Entwicklung", falling
    back to plain classification. DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC
    is likewise shared by the low-water dynamic boundaries and deciles —
    routed by whether "Dezile" appears in the requested abgeleiteteGroesse.
    DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC still only ever serves one
    quantity family, so it's routed by endpoint alone.
    DERIVED_ENDPOINT_HISTORICAL_STATISTICS is routed by the exact
    abgeleiteteGroesse value (e.g. "MQ", "NQ", "SumD Zeitfenster", "Tage
    unter GlWRNW/BWu aktueller Tag") via the historical_statistics
    override dict, keyed the same way — this single dict already covers
    every quantity sharing that endpoint, old and new.
    DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS (Sprint 7) is likewise routed
    by exact abgeleiteteGroesse via calendar_day_results, covering both
    the calendar-day envelope quantities and depth-below-ground.
    """
    client = AsyncMock()
    client.async_get_series.return_value = _series()

    historical_statistics = historical_statistics or {}
    dated_extremes = dated_extremes or {}
    calendar_day_results = calendar_day_results or {}

    async def _async_get_derived_result(endpoint: str, params: dict[str, str]) -> object:
        quantity = params["abgeleiteteGroesse"]

        if endpoint == DERIVED_ENDPOINT_LOW_WATER_CLASS:
            if "mit Datum" in quantity:
                result = dated_extremes.get(quantity, _dated_extreme_response())
            elif quantity == "unter GlW":
                result = below_glw or _below_glw_response()
            elif "Entwicklung" in quantity:
                result = official_development or _official_development_response()
            else:
                result = classification or _classification_response()
        elif endpoint == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_DYNAMIC:
            if "Dezile" in quantity:
                result = deciles or _decile_response()
            else:
                result = dynamic or _dynamic_boundaries_response()
        elif endpoint == DERIVED_ENDPOINT_LOW_WATER_BOUNDARIES_STATIC:
            result = static or _static_boundaries_response()
        elif endpoint == DERIVED_ENDPOINT_HISTORICAL_STATISTICS:
            result = historical_statistics.get(
                quantity, _historical_statistic_response()
            )
        elif endpoint == DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS:
            if quantity == "m unter Geländeoberkante":
                result = calendar_day_results.get(
                    quantity, _depth_below_ground_response()
                )
            else:
                result = calendar_day_results.get(quantity, _calendar_day_response())
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
    coordinator._calendar_day_statistics = None
    coordinator._calendar_day_statistics_date = None
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


@pytest.mark.parametrize(
    "quantity",
    ["MQ", "MNQ", "MW", "MNW", "NQ", "Median Q Statisch", "NW", "Median W bezogen auf Referenzzeitraum"],
)
@pytest.mark.asyncio
async def test_update_requests_expected_reference_period_statistic_parameters(
    quantity: str,
) -> None:
    """Test that every berechneEinzelwertNummer reference-period quantity uses the same params, no interval."""
    measurement_type = (
        HydroMeasurementType.DISCHARGE
        if quantity in ("MQ", "MNQ", "NQ", "Median Q Statisch")
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
async def test_update_merges_group_b_statistics_on_success() -> None:
    """Test that NQ/Median Q Statisch (discharge) and NW/Median W (water_level) populate correctly."""
    discharge_observation = await _coordinator(_routed_client())._async_update_data()
    assert discharge_observation.nq is not None
    assert discharge_observation.nq.value == pytest.approx(42.0)
    assert discharge_observation.median_q is not None
    assert discharge_observation.nw is None
    assert discharge_observation.median_w is None

    water_level_observation = await _coordinator(
        _routed_client(), HydroMeasurementType.WATER_LEVEL
    )._async_update_data()
    assert water_level_observation.nw is not None
    assert water_level_observation.median_w is not None
    assert water_level_observation.nq is None
    assert water_level_observation.median_q is None


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


# --- Group A: historical calendar-day envelope ---------------------------


@pytest.mark.asyncio
async def test_update_merges_calendar_day_statistics_on_success() -> None:
    """Test that min/median/max_q populate for discharge, median_w stays None."""
    observation = await _coordinator(_routed_client())._async_update_data()

    assert observation.min_q_calendar_day is not None
    assert observation.min_q_calendar_day.value == pytest.approx(42.0)
    assert observation.median_q_calendar_day is not None
    assert observation.max_q_calendar_day is not None
    assert observation.median_w_calendar_day is None


@pytest.mark.asyncio
async def test_update_merges_calendar_day_statistics_on_success_for_water_level() -> None:
    """Test that median_w populates for water_level, the Q-quantities stay None."""
    observation = await _coordinator(
        _routed_client(), HydroMeasurementType.WATER_LEVEL
    )._async_update_data()

    assert observation.median_w_calendar_day is not None
    assert observation.median_w_calendar_day.value == pytest.approx(42.0)
    assert observation.min_q_calendar_day is None
    assert observation.median_q_calendar_day is None
    assert observation.max_q_calendar_day is None


@pytest.mark.asyncio
async def test_update_survives_calendar_day_statistic_failure() -> None:
    """Test that a failed calendar-day fetch does not fail the whole update."""
    client = _routed_client(
        calendar_day_results={
            "Min Q pro Kalendartag": NiwisConnectionError("min_q down")
        }
    )

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.min_q_calendar_day is not None
    assert observation.min_q_calendar_day.value is None
    assert observation.min_q_calendar_day.error == "min_q down"
    # Other calendar-day quantities are unaffected by the min_q failure.
    assert observation.median_q_calendar_day is not None
    assert observation.median_q_calendar_day.value == pytest.approx(42.0)


@pytest.mark.asyncio
async def test_calendar_day_statistics_are_cached_within_the_same_day() -> None:
    """Test that a second same-day update reuses the cached calendar-day dict."""
    client = _routed_client()
    coordinator = _coordinator(client)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    calendar_day_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS
        and call.args[1]["abgeleiteteGroesse"] == "Min Q pro Kalendartag"
    ]
    assert len(calendar_day_calls) == 1


@pytest.mark.asyncio
async def test_calendar_day_statistics_refetch_after_day_rollover() -> None:
    """Test that a calendar-day rollover triggers a refetch."""
    client = _routed_client()
    coordinator = _coordinator(client)

    with patch("custom_components.hydro_monitor.coordinator.date") as mock_date:
        mock_date.today.return_value = date(2026, 1, 1)
        await coordinator._async_update_data()

        mock_date.today.return_value = date(2026, 1, 2)
        await coordinator._async_update_data()

    calendar_day_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS
        and call.args[1]["abgeleiteteGroesse"] == "Min Q pro Kalendartag"
    ]
    assert len(calendar_day_calls) == 2


@pytest.mark.asyncio
async def test_calendar_day_statistic_failure_is_still_cached_within_the_day() -> None:
    """Test that, unlike deciles, a failed quantity is cached with the rest of the dict.

    Deliberately different from _async_fetch_dynamic_boundaries_cached's
    "don't cache on failure" behaviour: the whole 4-quantity dict is
    cached together once fetched, since each quantity's own error is
    already recorded on its own HydroCalendarDayValue.
    """
    client = _routed_client(
        calendar_day_results={
            "Min Q pro Kalendartag": NiwisConnectionError("min_q down")
        }
    )
    coordinator = _coordinator(client)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    calendar_day_calls = [
        call
        for call in client.async_get_derived_result.await_args_list
        if call.args[0] == DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS
        and call.args[1]["abgeleiteteGroesse"] == "Min Q pro Kalendartag"
    ]
    assert len(calendar_day_calls) == 1


@pytest.mark.asyncio
async def test_update_requests_expected_calendar_day_parameters() -> None:
    """Test the exact endpoint and params sent for a calendar-day request."""
    client = _routed_client()

    await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS,
        {
            "abgeleiteteGroesse": "Median Q pro Kalendertag",
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
async def test_calendar_day_statistics_not_fetched_for_unsupported_types(
    measurement_type: HydroMeasurementType,
) -> None:
    """Test that groundwater/spring-discharge coordinators skip the calendar-day quantities.

    berechneZeitreihenErgebnisNummer itself may still be called for
    groundwater_level (depth-below-ground, Group F, a different
    abgeleiteteGroesse on the same shared/overloaded endpoint), so this
    checks the specific quantity names rather than the endpoint broadly.
    """
    client = _routed_client()

    observation = await _coordinator(client, measurement_type)._async_update_data()

    assert observation.min_q_calendar_day is None
    assert observation.median_q_calendar_day is None
    assert observation.max_q_calendar_day is None
    assert observation.median_w_calendar_day is None

    for call in client.async_get_derived_result.await_args_list:
        if call.args[0] == DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS:
            assert (
                call.args[1]["abgeleiteteGroesse"]
                not in CALENDAR_DAY_STATISTIC_NIWIS_NAMES.values()
            )


# --- Group C: NM7Q/NM30Q mit Datum ----------------------------------------


@pytest.mark.asyncio
async def test_update_merges_dated_extremes_on_success() -> None:
    """Test that nm7q_dated/nm30q_dated are parsed and merged for discharge."""
    observation = await _coordinator(_routed_client())._async_update_data()

    assert observation.nm7q_dated is not None
    assert observation.nm7q_dated.value == pytest.approx(15.26)
    assert observation.nm7q_dated.occurred_from == date(2026, 7, 15)
    assert observation.nm7q_dated.occurred_to == date(2026, 7, 21)
    assert observation.nm7q_dated.unit == "m³/s"
    assert observation.nm30q_dated is not None


@pytest.mark.asyncio
async def test_dated_extremes_not_fetched_for_unsupported_types() -> None:
    """Test that non-discharge coordinators skip NM7Q/NM30Q mit Datum."""
    client = _routed_client()

    observation = await _coordinator(
        client, HydroMeasurementType.WATER_LEVEL
    )._async_update_data()

    assert observation.nm7q_dated is None
    assert observation.nm30q_dated is None

    for call in client.async_get_derived_result.await_args_list:
        assert "mit Datum" not in call.args[1]["abgeleiteteGroesse"]


@pytest.mark.asyncio
async def test_update_survives_dated_extreme_failure() -> None:
    """Test that a failed NM7Q mit Datum fetch does not fail the whole update."""
    client = _routed_client(
        dated_extremes={"NM7Q mit Datum": NiwisConnectionError("nm7q dated down")}
    )

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.nm7q_dated is not None
    assert observation.nm7q_dated.error == "nm7q dated down"
    assert observation.nm30q_dated is not None
    assert observation.nm30q_dated.value == pytest.approx(15.26)


@pytest.mark.asyncio
async def test_update_requests_expected_dated_extreme_parameters() -> None:
    """Test that NM7Q mit Datum reuses the same 30-day interval as plain NM7Q."""
    client = _routed_client()

    with patch("custom_components.hydro_monitor.coordinator.date") as mock_date:
        mock_date.today.return_value = date(2026, 7, 22)
        await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_LOW_WATER_CLASS,
        {
            "abgeleiteteGroesse": "NM7Q mit Datum",
            "messstelleNr": "DESM_DEBY16607001",
            "von": "2026-06-22",
            "bis": "2026-07-22",
        },
    )


# --- Group D: SumD/SumV Zeitfenster ---------------------------------------


@pytest.mark.asyncio
async def test_update_merges_sum_statistics_on_success() -> None:
    """Test that sum_d/sum_v populate for discharge."""
    observation = await _coordinator(_routed_client())._async_update_data()

    assert observation.sum_d is not None
    assert observation.sum_d.value == pytest.approx(42.0)
    assert observation.sum_v is not None


@pytest.mark.asyncio
async def test_sum_statistics_not_fetched_for_unsupported_types() -> None:
    """Test that non-discharge coordinators skip SumD/SumV Zeitfenster."""
    client = _routed_client()

    observation = await _coordinator(
        client, HydroMeasurementType.WATER_LEVEL
    )._async_update_data()

    assert observation.sum_d is None
    assert observation.sum_v is None

    for call in client.async_get_derived_result.await_args_list:
        assert call.args[1]["abgeleiteteGroesse"] not in (
            "SumD Zeitfenster",
            "SumV Zeitfenster",
        )


@pytest.mark.asyncio
async def test_update_survives_sum_statistic_failure() -> None:
    """Test that a failed SumD fetch does not fail the whole update."""
    client = _routed_client(
        historical_statistics={"SumD Zeitfenster": NiwisConnectionError("sumd down")}
    )

    observation = await _coordinator(client)._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.sum_d is not None
    assert observation.sum_d.error == "sumd down"
    assert observation.sum_v is not None
    assert observation.sum_v.value == pytest.approx(42.0)


@pytest.mark.asyncio
async def test_update_requests_expected_sum_parameters() -> None:
    """Test that SumD Zeitfenster combines a reference period AND an interval."""
    client = _routed_client()

    with patch("custom_components.hydro_monitor.coordinator.date") as mock_date:
        mock_date.today.return_value = date(2026, 7, 22)
        await _coordinator(client)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
        {
            "abgeleiteteGroesse": "SumD Zeitfenster",
            "messstelleNr": "DESM_DEBY16607001",
            "jahresdefinition": "KALENDERJAHR",
            "startJahr": "1991",
            "endJahr": "2020",
            "von": "2026-06-22",
            "bis": "2026-07-22",
        },
    )


# --- Group E: waterway navigation indicators ------------------------------


@pytest.mark.asyncio
async def test_update_merges_waterway_indicators_on_success() -> None:
    """Test that below_glw/days_below_glw populate for water_level."""
    observation = await _coordinator(
        _routed_client(), HydroMeasurementType.WATER_LEVEL
    )._async_update_data()

    assert observation.below_glw == "unterhalb"
    assert observation.below_glw_raw == "unterhalb"
    assert observation.below_glw_error is None
    assert observation.days_below_glw is not None
    assert observation.days_below_glw.value == pytest.approx(42.0)


@pytest.mark.asyncio
async def test_waterway_indicators_not_fetched_for_unsupported_types() -> None:
    """Test that discharge coordinators skip the waterway indicators (water_level only)."""
    client = _routed_client()

    observation = await _coordinator(client)._async_update_data()

    assert observation.below_glw is None
    assert observation.days_below_glw is None

    for call in client.async_get_derived_result.await_args_list:
        assert call.args[1]["abgeleiteteGroesse"] not in (
            "unter GlW",
            "Tage unter GlWRNW/BWu aktueller Tag",
        )


@pytest.mark.asyncio
async def test_update_survives_waterway_indicator_failure() -> None:
    """Test that a failed 'unter GlW' fetch does not fail the whole update."""
    client = _routed_client(below_glw=NiwisConnectionError("glw down"))

    observation = await _coordinator(
        client, HydroMeasurementType.WATER_LEVEL
    )._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.below_glw is None
    assert observation.below_glw_error == "glw down"
    # days_below_glw is unaffected by the below_glw failure.
    assert observation.days_below_glw is not None


@pytest.mark.asyncio
async def test_update_requests_expected_waterway_indicator_parameters() -> None:
    """Test that the waterway indicators need neither a reference period nor an interval."""
    client = _routed_client()

    await _coordinator(client, HydroMeasurementType.WATER_LEVEL)._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_LOW_WATER_CLASS,
        {"abgeleiteteGroesse": "unter GlW", "messstelleNr": "DESM_DEBY16607001"},
    )
    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_HISTORICAL_STATISTICS,
        {
            "abgeleiteteGroesse": "Tage unter GlWRNW/BWu aktueller Tag",
            "messstelleNr": "DESM_DEBY16607001",
        },
    )


# --- Group F: groundwater depth below ground ------------------------------


@pytest.mark.asyncio
async def test_update_merges_depth_below_ground_on_success() -> None:
    """Test that depth_below_ground picks the newest value in the interval."""
    observation = await _coordinator(
        _routed_client(), HydroMeasurementType.GROUNDWATER_LEVEL
    )._async_update_data()

    assert observation.depth_below_ground is not None
    assert observation.depth_below_ground.value == pytest.approx(12.5)
    assert observation.depth_below_ground.unit == "m"


@pytest.mark.asyncio
async def test_depth_below_ground_not_fetched_for_unsupported_types() -> None:
    """Test that non-groundwater coordinators skip depth-below-ground."""
    client = _routed_client()

    observation = await _coordinator(client)._async_update_data()

    assert observation.depth_below_ground is None

    for call in client.async_get_derived_result.await_args_list:
        assert call.args[1]["abgeleiteteGroesse"] != "m unter Geländeoberkante"


@pytest.mark.asyncio
async def test_update_survives_depth_below_ground_failure() -> None:
    """Test that a failed depth-below-ground fetch does not fail the whole update."""
    client = _routed_client(
        calendar_day_results={
            "m unter Geländeoberkante": NiwisConnectionError("depth down")
        }
    )

    observation = await _coordinator(
        client, HydroMeasurementType.GROUNDWATER_LEVEL
    )._async_update_data()

    assert observation.value == pytest.approx(10.5)
    assert observation.depth_below_ground is not None
    assert observation.depth_below_ground.error == "depth down"


@pytest.mark.asyncio
async def test_update_requests_expected_depth_below_ground_parameters() -> None:
    """Test that depth-below-ground uses a 30-day interval, no reference period."""
    client = _routed_client()

    with patch("custom_components.hydro_monitor.coordinator.date") as mock_date:
        mock_date.today.return_value = date(2026, 7, 22)
        await _coordinator(
            client, HydroMeasurementType.GROUNDWATER_LEVEL
        )._async_update_data()

    client.async_get_derived_result.assert_any_await(
        DERIVED_ENDPOINT_CALENDAR_DAY_STATISTICS,
        {
            "abgeleiteteGroesse": "m unter Geländeoberkante",
            "messstelleNr": "DESM_DEBY16607001",
            "von": "2026-06-22",
            "bis": "2026-07-22",
        },
    )

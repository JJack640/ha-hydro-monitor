"""Tests for Hydro Monitor system health information."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.hydro_monitor.system_health import (
    async_register,
    async_system_health_info,
)


def _loaded_entry(
    *,
    station_id: str = "DESM_DEBY16607001",
    last_update_success: bool = True,
    observed_on: date | None = date(2026, 10, 15),
    update_interval: timedelta | None = timedelta(hours=6),
) -> SimpleNamespace:
    """Create a config entry that finished setup and carries runtime_data."""
    coordinator = SimpleNamespace(
        last_update_success=last_update_success,
        update_interval=update_interval,
        data=(
            SimpleNamespace(observed_on=observed_on)
            if observed_on is not None
            else None
        ),
    )
    return SimpleNamespace(
        state=ConfigEntryState.LOADED,
        runtime_data=SimpleNamespace(
            station=SimpleNamespace(provider="niwis", station_id=station_id),
            coordinator=coordinator,
        ),
    )


def _unloaded_entry(state: ConfigEntryState) -> SimpleNamespace:
    """Create a config entry that is not loaded.

    Like a real Home Assistant ConfigEntry before setup succeeded (e.g. while
    retrying during a NIWIS outage), it has NO runtime_data attribute at all:
    reading it raises AttributeError rather than returning None.
    """
    return SimpleNamespace(state=state)


def _hass(*entries: SimpleNamespace) -> MagicMock:
    """Create a hass double whose config entries are the given ones."""
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = list(entries)
    return hass


@pytest.mark.asyncio
async def test_info_for_a_loaded_entry() -> None:
    """Test the reported values for one healthy, loaded entry."""
    info = await async_system_health_info(_hass(_loaded_entry()))

    assert info == {
        "Configured entries": 1,
        "Loaded entries": 1,
        "Configured stations": 1,
        "Providers": "NIWIS",
        "Last update successful": True,
        "Update interval": "6 hours",
        "Latest observation": date(2026, 10, 15),
    }


@pytest.mark.asyncio
async def test_unloaded_entry_does_not_raise() -> None:
    """Test an entry still retrying setup is counted but does not break the info.

    Regression for the review note on the HACS submission: reading
    runtime_data on a not-loaded entry raised AttributeError, which made
    Home Assistant log a traceback and show an error under "System
    information".
    """
    info = await async_system_health_info(
        _hass(
            _loaded_entry(),
            _unloaded_entry(ConfigEntryState.SETUP_RETRY),
        )
    )

    assert info["Configured entries"] == 2
    assert info["Loaded entries"] == 1
    assert info["Configured stations"] == 1
    assert info["Last update successful"] is True


@pytest.mark.parametrize(
    "state",
    [
        ConfigEntryState.SETUP_RETRY,
        ConfigEntryState.SETUP_ERROR,
        ConfigEntryState.SETUP_IN_PROGRESS,
        ConfigEntryState.NOT_LOADED,
        ConfigEntryState.FAILED_UNLOAD,
    ],
)
@pytest.mark.asyncio
async def test_only_unloaded_entries_report_nothing_loaded(
    state: ConfigEntryState,
) -> None:
    """Test every non-loaded state yields counts but no station details."""
    info = await async_system_health_info(_hass(_unloaded_entry(state)))

    assert info == {
        "Configured entries": 1,
        "Loaded entries": 0,
        "Configured stations": 0,
        "Providers": None,
        "Last update successful": None,
        "Update interval": None,
        "Latest observation": None,
    }


@pytest.mark.asyncio
async def test_no_entries() -> None:
    """Test the empty configuration."""
    info = await async_system_health_info(_hass())

    assert info["Configured entries"] == 0
    assert info["Loaded entries"] == 0
    assert info["Last update successful"] is None


@pytest.mark.asyncio
async def test_failed_update_is_reported() -> None:
    """Test that one failing coordinator turns 'Last update successful' off."""
    info = await async_system_health_info(
        _hass(
            _loaded_entry(),
            _loaded_entry(station_id="DEGM_DEBY16232", last_update_success=False),
        )
    )

    assert info["Loaded entries"] == 2
    assert info["Configured stations"] == 2
    assert info["Last update successful"] is False


@pytest.mark.asyncio
async def test_latest_observation_is_the_newest_across_entries() -> None:
    """Test the newest observation date wins, and entries without data are skipped."""
    info = await async_system_health_info(
        _hass(
            _loaded_entry(observed_on=date(2026, 10, 14)),
            _loaded_entry(station_id="DEGM_DEBY16232", observed_on=date(2026, 10, 16)),
            _loaded_entry(station_id="DEGM_DEBY15500", observed_on=None),
        )
    )

    assert info["Latest observation"] == date(2026, 10, 16)


@pytest.mark.asyncio
async def test_mixed_update_intervals_are_listed() -> None:
    """Test differing update intervals are all shown, sorted."""
    info = await async_system_health_info(
        _hass(
            _loaded_entry(update_interval=timedelta(hours=12)),
            _loaded_entry(station_id="DEGM_DEBY16232", update_interval=timedelta(hours=6)),
        )
    )

    assert info["Update interval"] == "6 h, 12 h"


def test_register_adds_the_info_callback() -> None:
    """Test the integration registers its info callback with system health."""
    register = MagicMock()

    async_register(MagicMock(), register)

    register.async_register_info.assert_called_once_with(async_system_health_info)


@pytest.mark.asyncio
async def test_latest_observation_orders_days_and_points_in_time() -> None:
    """Test providers reporting a day and providers reporting a time mix safely.

    NIWIS reports a calendar day, finer providers a timestamp; comparing the
    two directly raises TypeError.
    """
    newest = datetime(2026, 10, 23, 12, 15, tzinfo=UTC)

    info = await async_system_health_info(
        _hass(
            _loaded_entry(observed_on=date(2026, 10, 22)),
            _loaded_entry(station_id="uuid-1", observed_on=newest),
            _loaded_entry(station_id="DEGM_DEBY15500", observed_on=date(2026, 10, 23)),
        )
    )

    assert info["Latest observation"] == newest


@pytest.mark.asyncio
async def test_a_day_after_an_earlier_timestamp_wins() -> None:
    """Test a calendar day counts from its start (midnight UTC)."""
    info = await async_system_health_info(
        _hass(
            _loaded_entry(observed_on=datetime(2026, 10, 22, 23, 0, tzinfo=UTC)),
            _loaded_entry(station_id="DEGM_DEBY15500", observed_on=date(2026, 10, 23)),
        )
    )

    assert info["Latest observation"] == date(2026, 10, 23)

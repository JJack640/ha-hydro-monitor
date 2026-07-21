"""Config flow for the Hydro Monitor integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_MEASUREMENT_TYPE,
    CONF_PROVIDER,
    CONF_STATION_ID,
    DOMAIN,
    NEARBY_STATION_LIMIT,
    PROVIDER_NIWIS,
)
from .core.station_discovery import StationDiscoveryService
from .models import HydroMeasurementType, HydroStation
from .providers.niwis.api import NiwisError


def _station_label(station: HydroStation) -> str:
    """Return a user-friendly label for a station."""
    parts = [station.name]

    if station.waterbody:
        parts.append(station.waterbody)

    if station.distance_km is not None:
        parts.append(f"{station.distance_km:.1f} km")

    return " · ".join(parts)


class HydroMonitorConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for Hydro Monitor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the Hydro Monitor config flow."""
        self._measurement_type: HydroMeasurementType | None = None
        self._stations: dict[str, HydroStation] = {}

    def _measurement_type_display_name(self) -> str:
        """Return a readable measurement type for the config entry title."""
        if self._measurement_type is None:
            return ""

        return {
            HydroMeasurementType.DISCHARGE: "Discharge",
            HydroMeasurementType.WATER_LEVEL: "Water level",
            HydroMeasurementType.GROUNDWATER_LEVEL: "Groundwater level",
            HydroMeasurementType.SPRING_DISCHARGE: "Spring discharge",
        }[self._measurement_type]

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle measurement type selection."""
        if user_input is not None:
            self._measurement_type = HydroMeasurementType(
                user_input[CONF_MEASUREMENT_TYPE]
            )
            self._stations = {}
            return await self.async_step_station()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MEASUREMENT_TYPE): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                measurement_type.value
                                for measurement_type in HydroMeasurementType
                            ],
                            translation_key="measurement_type",
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_station(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle station discovery and selection."""
        if self._measurement_type is None:
            return await self.async_step_user()

        if not self._stations:
            try:
                discovery = StationDiscoveryService(self.hass)
                discovered_stations = await discovery.async_discover(
                    self._measurement_type,
                    limit=NEARBY_STATION_LIMIT,
                )
            except NiwisError:
                return self.async_abort(reason="cannot_connect")

            if not discovered_stations:
                return self.async_abort(reason="no_stations_found")

            self._stations = {
                station.station_id: station for station in discovered_stations
            }

        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]
            station = self._stations[station_id]

            await self.async_set_unique_id(
                (f"{PROVIDER_NIWIS}:{station_id}:{self._measurement_type.value}")
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=(f"{station.name} – {self._measurement_type_display_name()}"),
                data={
                    CONF_PROVIDER: PROVIDER_NIWIS,
                    CONF_STATION_ID: station_id,
                    CONF_MEASUREMENT_TYPE: self._measurement_type.value,
                },
            )

        station_options = [
            SelectOptionDict(
                value=station.station_id,
                label=_station_label(station),
            )
            for station in self._stations.values()
        ]

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=station_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            sort=False,
                        )
                    )
                }
            ),
            description_placeholders={"measurement_type": self._measurement_type.value},
        )

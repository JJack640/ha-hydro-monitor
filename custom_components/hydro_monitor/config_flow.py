from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
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
from .models import HydroMeasurementType

LABELS = {
    HydroMeasurementType.GROUNDWATER_LEVEL: "Grundwasserstand",
    HydroMeasurementType.WATER_LEVEL: "Wasserstand",
    HydroMeasurementType.DISCHARGE: "Abfluss",
    HydroMeasurementType.SPRING_DISCHARGE: "Quellschüttung",
}


class HydroMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.mt = None
        self.stations = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self.mt = HydroMeasurementType(user_input[CONF_MEASUREMENT_TYPE])
            return await self.async_step_station()
        opts = [
            SelectOptionDict(value=x.value, label=LABELS[x])
            for x in HydroMeasurementType
        ]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MEASUREMENT_TYPE): SelectSelector(
                        SelectSelectorConfig(options=opts, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def async_step_station(self, user_input: dict[str, Any] | None = None):
        if self.mt is None:
            return await self.async_step_user()
        if not self.stations:
            try:
                discovery = StationDiscoveryService(self.hass)
                stations = await discovery.async_discover(
                    self.mt,
                    limit=NEARBY_STATION_LIMIT,
                )
            except Exception:
                return self.async_abort(reason="cannot_connect")
            self.stations = {s.station_id: s for s in stations}
        if user_input is not None:
            sid = user_input[CONF_STATION_ID]
            s = self.stations[sid]
            await self.async_set_unique_id(f"{PROVIDER_NIWIS}:{sid}:{self.mt.value}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{s.name} – {LABELS[self.mt]}",
                data={
                    CONF_PROVIDER: PROVIDER_NIWIS,
                    CONF_STATION_ID: sid,
                    CONF_MEASUREMENT_TYPE: self.mt.value,
                },
            )
        opts = [
            SelectOptionDict(
                value=s.station_id,
                label=f"{s.name}{' · ' + s.waterbody if s.waterbody else ''} · {s.distance_km:.1f} km",
            )
            for s in self.stations.values()
        ]
        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=opts, mode=SelectSelectorMode.DROPDOWN, sort=False
                        )
                    )
                }
            ),
            description_placeholders={"measurement_type": LABELS[self.mt]},
        )

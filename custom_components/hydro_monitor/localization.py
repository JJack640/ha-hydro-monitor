"""Shared localization for text that has no Home Assistant translation_key.

Entity names/states go through Home Assistant's translation_key mechanism
(translations/en.json, translations/de.json) and are localized per viewing
user automatically. Device name/model text and config entry titles have no
equivalent mechanism -- Home Assistant renders them as plain, stored text --
so they must be resolved manually against the instance-wide configured
language (hass.config.language) at the point they are created/computed.
"""

from __future__ import annotations

from typing import Final

from homeassistant.core import HomeAssistant

from .models import HydroMeasurementType

SUPPORTED_LANGUAGES: Final = ("en", "de")

DEVICE_MODEL_LABEL: Final = {
    "en": "Hydrological monitoring station",
    "de": "Hydrologische Messstelle",
}

MEASUREMENT_TYPE_NAMES: Final = {
    "en": {
        HydroMeasurementType.DISCHARGE: "Discharge",
        HydroMeasurementType.WATER_LEVEL: "Water level",
        HydroMeasurementType.GROUNDWATER_LEVEL: "Groundwater level",
        HydroMeasurementType.SPRING_DISCHARGE: "Spring discharge",
    },
    "de": {
        HydroMeasurementType.DISCHARGE: "Abfluss",
        HydroMeasurementType.WATER_LEVEL: "Wasserstand",
        HydroMeasurementType.GROUNDWATER_LEVEL: "Grundwasserstand",
        HydroMeasurementType.SPRING_DISCHARGE: "Quellschüttung",
    },
}


def resolve_language(hass: HomeAssistant | None) -> str:
    """Return "de" if Home Assistant is configured for German, else "en".

    Falls back to "en" for any other configured language, a missing/region-
    qualified language code (e.g. "de-DE" -> "de"), and defensively for test
    doubles or callers without a real HomeAssistant instance.
    """
    language = getattr(getattr(hass, "config", None), "language", None)
    language = (language or "en").split("-")[0].lower()
    return language if language in SUPPORTED_LANGUAGES else "en"


def measurement_type_name(
    measurement_type: HydroMeasurementType,
    language: str,
) -> str:
    """Return the localized display name for a measurement type."""
    return MEASUREMENT_TYPE_NAMES[language][measurement_type]


def device_model(
    measurement_type: HydroMeasurementType,
    language: str,
) -> str:
    """Return the localized device model string for a measurement type."""
    return (
        f"{DEVICE_MODEL_LABEL[language]} "
        f"({measurement_type_name(measurement_type, language)})"
    )

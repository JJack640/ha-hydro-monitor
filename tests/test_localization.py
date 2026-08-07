"""Tests for shared non-entity localization helpers."""

from unittest.mock import MagicMock

import pytest

from custom_components.hydro_monitor.localization import (
    device_model,
    measurement_type_name,
    resolve_language,
)
from custom_components.hydro_monitor.models import HydroMeasurementType


@pytest.mark.parametrize(
    ("configured_language", "expected"),
    [
        ("de", "de"),
        ("de-DE", "de"),
        ("en", "en"),
        ("en-US", "en"),
        ("fr", "en"),
        (None, "en"),
        ("", "en"),
    ],
)
def test_resolve_language(configured_language: str | None, expected: str) -> None:
    """Test language resolution: base-language extraction and safe fallback."""
    hass = MagicMock()
    hass.config.language = configured_language

    assert resolve_language(hass) == expected


def test_resolve_language_without_hass() -> None:
    """Test the defensive fallback for a missing/None hass (e.g. test doubles)."""
    assert resolve_language(None) == "en"


@pytest.mark.parametrize(
    ("measurement_type", "language", "expected"),
    [
        (HydroMeasurementType.DISCHARGE, "en", "Discharge"),
        (HydroMeasurementType.DISCHARGE, "de", "Abfluss"),
        (HydroMeasurementType.WATER_LEVEL, "de", "Wasserstand"),
        (HydroMeasurementType.GROUNDWATER_LEVEL, "de", "Grundwasserstand"),
        (HydroMeasurementType.SPRING_DISCHARGE, "de", "Quellschüttung"),
    ],
)
def test_measurement_type_name(
    measurement_type: HydroMeasurementType, language: str, expected: str
) -> None:
    """Test the localized measurement type names used outside entity names."""
    assert measurement_type_name(measurement_type, language) == expected


def test_device_model() -> None:
    """Test the composed device model string in both supported languages."""
    assert (
        device_model(HydroMeasurementType.DISCHARGE, "en")
        == "Hydrological monitoring station (Discharge)"
    )
    assert (
        device_model(HydroMeasurementType.DISCHARGE, "de")
        == "Hydrologische Messstelle (Abfluss)"
    )

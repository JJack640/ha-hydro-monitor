"""Registry of the data providers Hydro Monitor can use."""

from __future__ import annotations

from ..models import HydroMeasurementType
from .base import ProviderDefinition, ProviderError
from .niwis.provider import NIWIS_PROVIDER
from .pegelonline.provider import PEGELONLINE_PROVIDER

__all__ = [
    "PROVIDERS",
    "ProviderDefinition",
    "ProviderError",
    "get_provider",
    "providers_for",
]

PROVIDERS: dict[str, ProviderDefinition] = {
    NIWIS_PROVIDER.id: NIWIS_PROVIDER,
    PEGELONLINE_PROVIDER.id: PEGELONLINE_PROVIDER,
}


def get_provider(provider_id: str) -> ProviderDefinition:
    """Return the provider with the given id.

    Raises KeyError for an unknown id.
    """
    return PROVIDERS[provider_id]


def providers_for(
    measurement_type: HydroMeasurementType,
) -> list[ProviderDefinition]:
    """Return the providers that offer a measurement type."""
    return [
        provider
        for provider in PROVIDERS.values()
        if measurement_type in provider.measurement_types
    ]

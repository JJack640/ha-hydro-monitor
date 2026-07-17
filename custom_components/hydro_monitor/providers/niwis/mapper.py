"""Map NIWIS API data to provider-neutral Hydro Monitor models."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ...models import HydroMeasurementType, HydroObservation, HydroStation
from .const import NIWIS_TO_HYDRO_TYPE

INVALID_MEASUREMENT_VALUES = {
    -777.0,
    -888.0,
    -999.0,
    -9999.0,
}


def as_float(value: Any) -> float | None:
    """Convert a NIWIS value to float."""
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    """Parse a NIWIS observation date."""
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _is_valid_measurement(value: float | None) -> bool:
    """Return whether a NIWIS measurement is usable.

    NIWIS uses large negative values such as -777 as technical placeholders.
    Reject the complete placeholder range instead of only exact sentinel values.
    """
    return value is not None and value > -700.0


def station_from_niwis(
    data: dict[str, Any],
    distance_km: float | None = None,
) -> HydroStation:
    """Map a NIWIS station record."""
    measurement_types = tuple(
        HydroMeasurementType(NIWIS_TO_HYDRO_TYPE[item])
        for item in data.get("messgroesse", [])
        if item in NIWIS_TO_HYDRO_TYPE
    )

    return HydroStation(
        "niwis",
        str(data["messstelleNr"]),
        str(data.get("name") or data["messstelleNr"]),
        measurement_types,
        as_float(data.get("breite")),
        as_float(data.get("laenge")),
        data.get("gewaesser"),
        data.get("betreiber"),
        data.get("institution"),
        data.get("urlMessstelle"),
        data.get("lizenz"),
        distance_km,
    )


def observation_from_niwis(
    measurement_type: HydroMeasurementType,
    series: list[dict[str, Any]],
) -> HydroObservation:
    """Map the newest valid NIWIS observation and calculate trends.

    Technical NIWIS placeholder values such as -777 are ignored both
    for the current measurement and for historical trend values.
    """
    if not series:
        return HydroObservation(
            measurement_type,
            None,
            None,
            None,
        )

    valid_observations: list[tuple[date, dict[str, Any], float]] = []

    for item in series:
        value = as_float(item.get("messwert"))
        observed_on = _parse_date(item.get("datum"))

        if observed_on is None:
            continue

        if not _is_valid_measurement(value):
            continue

        valid_observations.append(
            (
                observed_on,
                item,
                value,
            )
        )

    if not valid_observations:
        return HydroObservation(
            measurement_type,
            None,
            None,
            None,
            sample_count=0,
        )

    valid_observations.sort(key=lambda observation: observation[0])

    observed_on, newest, value = valid_observations[-1]

    def value_at_or_before(
        target_date: date,
    ) -> float | None:
        """Return the newest valid value on or before a date."""
        matching_observations = [
            observation
            for observation in valid_observations
            if observation[0] <= target_date
        ]

        if not matching_observations:
            return None

        return matching_observations[-1][2]

    value_1d = value_at_or_before(observed_on - timedelta(days=1))
    value_7d = value_at_or_before(observed_on - timedelta(days=7))

    change_1d = value - value_1d if value_1d is not None else None
    change_7d = value - value_7d if value_7d is not None else None

    return HydroObservation(
        measurement_type,
        value,
        newest.get("einheit"),
        observed_on,
        newest.get("flag"),
        change_1d=change_1d,
        change_7d=change_7d,
        sample_count=len(valid_observations),
    )

"""Real PEGELONLINE captures (tools/pegelonline_discovery.py) for the tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INVENTORY_DIR = Path(__file__).resolve().parent.parent / "pegelonline_inventory"

KAUB = "1d26e504-7f9e-480a-b52c-5932be6549ab"
HAMM_UW = "4ef9dd9c-b32b-43fc-bc5e-3849d4ab7ecc"  # W in m+NN, every minute
AHLDEN = "522286e2-b2b3-4d0d-9a11-01b3ea418c76"  # stateMnwMhw "low"
CELLE = "b475386c-30cc-453a-b3b7-1d17ace13595"  # stateMnwMhw "normal"
HAMM_OW = "4dbce62d-a015-4011-afcd-423bb8d4b7a1"  # stateMnwMhw "unknown"
MELLUMPLATE = "c8b9a2b6-b783-417f-8479-3a0d732fb901"  # stateMnwMhw "commented"
HAMBURG_HARBURG = "706e5110-c5e2-4915-9989-c071fcb492ec"  # tidal, every minute
PRELOUC = "8e326085-c879-4704-95b4-c1fc19874176"  # Q only, no coordinates
DORDRECHT = "6c6f84c2-b7ea-4720-8ecd-a83c100c6291"  # no coordinates
ABBENFLETH = "28ec91e8"  # prefix: neither W nor Q


def stations_sample() -> dict[str, dict[str, Any]]:
    """Return the sample stations by case label."""
    return json.loads((INVENTORY_DIR / "stations_sample.json").read_text("utf-8"))


def station(uuid_prefix: str) -> dict[str, Any]:
    """Return one sample station by (the start of) its uuid."""
    for raw in stations_sample().values():
        if raw["uuid"].startswith(uuid_prefix):
            return raw

    raise KeyError(uuid_prefix)


def measurements(uuid: str, series: str) -> list[dict[str, Any]]:
    """Return the captured measurements of a station's series."""
    return json.loads(
        (INVENTORY_DIR / "measurements" / f"{uuid}__{series}.json").read_text("utf-8")
    )


def timeseries(uuid: str, series: str) -> dict[str, Any]:
    """Return the captured time series with its current measurement."""
    return json.loads(
        (INVENTORY_DIR / "timeseries" / f"{uuid}__{series}.json").read_text("utf-8")
    )


def errors() -> dict[str, Any]:
    """Return the captured error answers."""
    return json.loads((INVENTORY_DIR / "errors.json").read_text("utf-8"))

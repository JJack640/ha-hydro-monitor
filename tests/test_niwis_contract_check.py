"""Tests for the NIWIS API contract check (tools/niwis_contract_check.py)."""

import json
from pathlib import Path
from typing import Any

import pytest

from tools.niwis_contract_check import (
    check_catalogue,
    check_karte,
    expected_quantities,
)

INVENTORY_DIR = Path(__file__).resolve().parent.parent / "niwis_inventory"


def _catalogue(name: str) -> list[dict[str, Any]]:
    """Load a recorded real derived-quantity catalogue."""
    return json.loads((INVENTORY_DIR / name).read_text(encoding="utf-8"))


def test_expected_quantities_cover_every_requested_family() -> None:
    """Test the expectation list contains the quantities the coordinator requests."""
    names = {name for _endpoint, name in expected_quantities()}

    assert {
        "Abfluss Klassifikation mit variablen Grenzwerten",
        "Wasserstand Dezile tageweise",
        "Abfluss Entwicklung letzte 7 Tage",
        "NM7Q",
        "NM30Q",
        "unter GlW",
        "MQ",
        "SumD",
        "SumV",
        "Tage unter GlW",
        "m unter Geländeoberkante",
        "Min Q pro Kalendartag",
    } <= names
    # Removed server-side in 2026-10; must never be expected again.
    assert not any("Niedrigwasserklasse" in name for name in names)
    assert not any("mit Datum" in name or "Zeitfenster" in name for name in names)


def test_current_catalogue_matches_what_the_integration_requests() -> None:
    """Test the pinned 2026-10-16 NIWIS catalogue offers every expected quantity."""
    assert check_catalogue(_catalogue("derived_quantities_2026-10-16.json")) == []


def test_july_catalogue_drift_is_detected() -> None:
    """Test the check would have caught the real 2026-10 restructuring.

    The 2026-07-22 catalogue is what the integration was built against;
    against it the current expectations must report the quantities that
    were later renamed, moved or removed.
    """
    problems = "\n".join(check_catalogue(_catalogue("derived_quantities.json")))

    assert "'Tage unter GlW'" in problems
    assert "'NM7Q' is now on" in problems
    assert "'SumD' is now on" in problems
    assert "'m unter Geländeoberkante' is now on" in problems


def test_removed_quantity_is_reported_as_missing() -> None:
    """Test a quantity that disappears from the catalogue is flagged."""
    catalogue = [
        q
        for q in _catalogue("derived_quantities_2026-10-16.json")
        if q["abgeleiteteGroesse"] != "SumD"
    ]

    assert check_catalogue(catalogue) == [
        "missing: 'SumD' (expected on berechneEinzelwertNummer)"
    ]


def test_moved_quantity_is_reported_with_its_new_endpoint() -> None:
    """Test a quantity that changes endpoint is flagged with where it went."""
    catalogue = [dict(q) for q in _catalogue("derived_quantities_2026-10-16.json")]
    for quantity in catalogue:
        if quantity["abgeleiteteGroesse"] == "NM7Q":
            quantity["endpunkt"] = "berechneEinzelwertNummer"

    assert check_catalogue(catalogue) == [
        "moved: 'NM7Q' is now on ['berechneEinzelwertNummer'], "
        "expected berechneEinzelwertKategorie"
    ]


def test_karte_accepts_real_fixture() -> None:
    """Test a real captured classification list passes."""
    stations = json.loads(
        (INVENTORY_DIR / "karte" / "abfluss_dynamisch.json").read_text(
            encoding="utf-8"
        )
    )

    assert check_karte("discharge", stations) == []


@pytest.mark.parametrize("payload", [None, {}, [], "oops"])
def test_karte_rejects_non_list_or_empty_response(payload: object) -> None:
    """Test that a malformed or empty list is reported."""
    assert check_karte("discharge", payload) == [
        "karte/discharge: response is not a non-empty list"
    ]


def test_karte_reports_entry_without_required_fields() -> None:
    """Test that an entry missing nummer/niedrigwasserKlasse is reported."""
    problems = check_karte("discharge", [{"nummer": "X"}])

    assert len(problems) == 1
    assert "entry without nummer/niedrigwasserKlasse" in problems[0]


def test_karte_reports_unknown_class_value() -> None:
    """Test that a class value we cannot map is surfaced rather than ignored."""
    stations = [
        {"nummer": "X", "niedrigwasserKlasse": "NIEDRIG"},
        {"nummer": "Y", "niedrigwasserKlasse": "NEUE_KLASSE"},
    ]

    assert check_karte("water_level", stations) == [
        "karte/water_level: unknown class value(s) ['NEUE_KLASSE']"
    ]

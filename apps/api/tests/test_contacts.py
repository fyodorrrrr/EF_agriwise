from __future__ import annotations

from app.contacts import find_contact, municipalities, municipality_in


def test_province_falls_back_to_provincial_office():
    c = find_contact("Batangas")
    assert c is not None
    assert "Batangas" in c.scope
    assert c.phone


def test_no_province_falls_back_to_regional_da():
    c = find_contact(None)
    assert c is not None
    assert c.scope == "DA CALABARZON (regional)"
    assert "Regional Field Office" in c.organization


def test_municipality_match_wins_over_province():
    munis = municipalities()
    assert munis  # CSV present
    target = next((m for m in munis if "Bacoor" in m), munis[0])
    c = find_contact("Cavite", target)
    assert c is not None
    assert c.scope == target


def test_municipality_in_reads_the_question():
    munis = municipalities()
    target = next((m for m in munis if "Bacoor" in m), None)
    if target is None:
        return
    assert municipality_in(f"I farm near {target.lower()}, help me") == target
    assert municipality_in("just a rice question, no place") is None


def test_bogus_province_still_returns_regional():
    c = find_contact("Atlantis")
    assert c is not None and c.scope == "DA CALABARZON (regional)"

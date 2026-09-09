"""Sprint 3, Task 3.3 — analytical invariants that must hold across the API.

These lock behaviour the plan and ADR-001 commit to; a change here should
force a deliberate config/plan update.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.forecast_service import ForecastService

_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"


def _service() -> ForecastService:
    if not (_ARTIFACTS / "prepared").is_dir():
        pytest.skip("committed artifact bundle not present")
    return ForecastService(ArtifactRegistry.load(_ARTIFACTS))


def test_red_onion_synthetic_supply_price_and_opportunity_are_available():
    svc = _service()
    for province in ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal"):
        outlook = svc.outlook("Red Onion", province)
        assert outlook.supply.verdict == "CAUTION"
        assert outlook.price.verdict == "CAUTION"
        assert outlook.opportunity.verdict == "PASS"
        assert outlook.opportunity.score is not None


def test_no_supply_gap_anywhere_and_only_red_onion_has_physical_demand():
    """Physical Red Onion demand does not imply a physical supply-gap metric."""
    svc = _service()
    for commodity in ("Rice", "Tomato", "Red Onion", "Banana"):
        outlook = svc.outlook(commodity, "Laguna")
        if commodity == "Red Onion":
            assert outlook.demand.unit == "MT"
        else:
            assert outlook.demand.unit is None or "index" in outlook.demand.unit.lower()
        serialized = json.dumps(
            {
                "demand": outlook.demand.__dict__,
                "supply": outlook.supply.__dict__,
                "opportunity": outlook.opportunity.__dict__,
            },
            default=str,
        )
        assert "supply_gap_mt" not in serialized
        assert "gap_mt" not in serialized


def test_opportunity_weights_match_the_committed_config():
    """The scorer must not silently diverge from opportunity_scoring_config.json."""
    config = json.loads(
        (_ARTIFACTS / "config" / "opportunity_scoring_config.json").read_text()
    )
    svc = _service()
    opp = svc.outlook("Rice", "Laguna").opportunity
    assert opp.verdict == "PASS"

    configured = {
        k: v["weight"]
        for k, v in config["components"].items()
        if not v.get("optional")
    }
    total = sum(configured.values())
    for key, weight in opp.weights_used.items():
        assert weight == pytest.approx(configured[key] / total, rel=1e-3)


def test_repeated_requests_are_deterministic():
    svc = _service()
    first = svc.outlook("Rice", "Laguna")
    second = svc.outlook("Rice", "Laguna")
    assert first.demand.forecast == second.demand.forecast
    assert first.opportunity.score == second.opportunity.score

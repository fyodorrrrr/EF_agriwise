from __future__ import annotations

from pathlib import Path

import pytest

from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.forecast_service import ForecastService
from ml.forecasting.opportunity import OpportunityScorer

_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"

_CONFIG = {
    "schema_version": "3.2",
    "components": {
        "demand_pressure_index": {"weight": 0.35, "direction": "higher_better"},
        "supply_gap_or_scarcity_index": {"weight": 0.25, "direction": "higher_better"},
        "price_opportunity_index": {"weight": 0.20, "direction": "higher_better"},
        "market_flow_dependence_index": {"weight": 0.10, "optional": True},
        "forecast_confidence_index": {"weight": 0.10, "direction": "higher_better"},
    },
}

_PROVINCES = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def _peers(demand, supply, price, confidence=60.0):
    return {
        prov: {
            "demand": demand[i],
            "supply": supply[i],
            "price": price[i],
            "confidence": confidence,
        }
        for i, prov in enumerate(_PROVINCES)
    }


def test_scorer_renormalizes_weights_over_present_components():
    # market_flow has no input -> dropped; the other four (0.35+0.25+0.20+0.10)
    # renormalize over 0.90.
    result = OpportunityScorer(_CONFIG).score(
        "Laguna", _peers([1, 2, 3, 4, 5], [5, 4, 3, 2, 1], [1, 2, 3, 4, 5])
    )

    assert "market_flow_dependence_index" not in result.weights_used
    assert result.weights_used["demand_pressure_index"] == pytest.approx(0.35 / 0.90, rel=1e-3)
    assert sum(result.weights_used.values()) == pytest.approx(1.0)


def test_scarcity_rewards_the_lowest_supply_province():
    # Laguna has the highest demand, lowest supply, highest price -> top score.
    result = OpportunityScorer(_CONFIG).score(
        "Laguna",
        _peers([10, 20, 100, 5, 8], [100, 90, 5, 120, 110], [10, 12, 40, 9, 8]),
    )
    assert result.classification == "HIGH_OPPORTUNITY"
    assert result.breakdown["supply_gap_or_scarcity_index"]["score"] == 100.0


def test_scorer_fails_closed_on_a_missing_required_input():
    peers = _peers([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    peers["Cavite"]["price"] = None

    result = OpportunityScorer(_CONFIG).score("Laguna", peers)

    assert result.verdict == "INSUFFICIENT_DATA"
    assert result.score is None


def _real_service() -> ForecastService:
    if not (_ARTIFACTS / "prepared").is_dir():
        pytest.skip("committed artifact bundle not present in this checkout")
    return ForecastService(ArtifactRegistry.load(_ARTIFACTS))


def test_outlook_opportunity_scores_rice_and_synthetic_red_onion():
    svc = _real_service()

    rice = svc.outlook("Rice", "Laguna").opportunity
    assert rice.verdict == "PASS"
    assert 0 <= rice.score <= 100
    assert rice.classification in {
        "HIGH_OPPORTUNITY",
        "UNDERSUPPLY_LEANING",
        "BALANCED",
        "OVERSUPPLY_LEANING",
        "SEVERE_OVERSUPPLY",
    }
    assert rice.shared_quarter and rice.breakdown and rice.weights_used

    red_onion = svc.outlook("Red Onion", "Batangas").opportunity
    assert red_onion.verdict == "PASS"
    assert red_onion.score is not None

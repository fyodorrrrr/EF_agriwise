from __future__ import annotations

from pathlib import Path

import pytest

from app.rag_context import build_analytics_context
from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.forecast_service import ForecastService

_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"


def _service() -> ForecastService:
    if not (_ARTIFACTS / "prepared").is_dir():
        pytest.skip("committed artifact bundle not present")
    return ForecastService(ArtifactRegistry.load(_ARTIFACTS))


def test_returns_none_for_missing_or_bogus_selectors():
    svc = _service()
    assert build_analytics_context(svc, None, "Laguna") is None
    assert build_analytics_context(svc, "Rice", None) is None
    assert build_analytics_context(svc, "Gold", "Laguna") is None
    assert build_analytics_context(svc, "Rice", "Atlantis") is None


def test_rice_context_labels_demand_as_a_proxy_index_and_names_the_source():
    ctx = build_analytics_context(_service(), "Rice", "Laguna")

    assert "Rice in Laguna province" in ctx
    assert "Estimated Demand Proxy" in ctx
    assert "metric tonnes" not in ctx.split("Demand", 1)[1].split("\n", 1)[0]  # demand line
    assert "source" in ctx  # forecast source named
    assert "province-resolution" in ctx


def test_red_onion_context_marks_supply_price_and_opportunity_unavailable():
    ctx = build_analytics_context(_service(), "Red Onion", "Batangas")

    assert "Supply (metric tonnes, quarterly): not available" in ctx
    assert "Price (PHP/kg, monthly): not available" in ctx
    assert "Opportunity: not available" in ctx
    # ...but the demand proxy index is still reported
    assert "Demand (Estimated Demand Proxy, index): quality:" in ctx

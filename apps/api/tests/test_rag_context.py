from __future__ import annotations

from pathlib import Path

import pytest

from app.rag_context import build_analytics_context, build_full_grid_context
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
    # The full forecast series is present, not just the last quarter, so a
    # question about a specific quarter ("supply in Q3 2026") can be answered.
    import re

    assert re.search(r"forecast by period \[[^\]]*Q\d \d{4}[^\]]*Q\d \d{4}", ctx)


def test_full_grid_context_has_a_row_for_every_commodity_province_pair():
    ctx = build_full_grid_context(_service())
    assert ctx is not None
    assert "Full CALABARZON analytics grid" in ctx
    for commodity in ("Rice", "Tomato", "Red Onion", "Banana"):
        for province in ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal"):
            assert f"- {commodity} / {province}:" in ctx
    # Red Onion supply/price have no model — the grid says so, does not invent a number.
    onion_rows = [ln for ln in ctx.splitlines() if ln.startswith("- Red Onion /")]
    assert onion_rows and all("supply not available" in ln for ln in onion_rows)


def test_red_onion_context_marks_supply_price_and_opportunity_unavailable():
    ctx = build_analytics_context(_service(), "Red Onion", "Batangas")

    assert "Supply (metric tonnes, quarterly): not available" in ctx
    assert "Price (PHP/kg, monthly): not available" in ctx
    assert "Opportunity: not available" in ctx
    # ...but the demand proxy index is still reported
    assert "Demand (Estimated Demand Proxy, index): quality:" in ctx

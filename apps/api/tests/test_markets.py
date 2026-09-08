from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from markets.ranking import rank_markets
from markets.registry import MarketRegistry

_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"

client = TestClient(create_app())


def _registry() -> MarketRegistry:
    if not (_ARTIFACTS / "market_coordinates" / "CALABARZON_market_coordinates.csv").is_file():
        pytest.skip("market coordinates not present in this checkout")
    return MarketRegistry.load(_ARTIFACTS)


def test_registry_loads_only_valid_calabarzon_markets():
    registry = _registry()

    # ~40 of the 131 curated entries carry coordinates; the rest are name-only
    # and dropped (recorded in diagnostics) because they can't be mapped/ranked.
    assert 30 <= len(registry.markets) <= 60
    assert any("market row skipped" in d or "coordinates" in d for d in registry.diagnostics)
    ids = [m.market_id for m in registry.markets]
    assert len(ids) == len(set(ids))  # unique
    for m in registry.markets:
        assert m.province in ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")
        assert 13.0 <= m.latitude <= 15.2 and 120.0 <= m.longitude <= 122.3
        assert m.coordinate_confidence  # approximate points kept, never blank


def test_ranking_orders_by_score_and_explains_each_pick():
    registry = _registry()

    ranked = rank_markets(registry, province="Laguna", supported_analytics=3, limit=5)

    assert 1 <= len(ranked) <= 5
    assert all(r.market.province == "Laguna" for r in ranked)
    assert [r.score for r in ranked] == sorted((r.score for r in ranked), reverse=True)
    assert all("travel time" in r.why for r in ranked)  # distance caveat surfaced
    assert all(r.distance_km >= 0 for r in ranked)


def test_lower_analytics_support_lowers_every_score():
    registry = _registry()

    full = {
        r.market.market_id: r.score
        for r in rank_markets(registry, province="Cavite", supported_analytics=3)
    }
    none = {
        r.market.market_id: r.score
        for r in rank_markets(registry, province="Cavite", supported_analytics=0)
    }

    assert all(none[mid] < full[mid] for mid in full)


def test_markets_endpoints():
    listing = client.get("/markets", params={"province": "Rizal"}).json()
    assert listing["markets"] and all(m["province"] == "Rizal" for m in listing["markets"])

    ranked = client.get("/markets/rank", params={"commodity": "Rice", "province": "Rizal"}).json()
    assert ranked["supported_analytics"] == 3  # rice has demand+supply+price
    assert ranked["ranked"]
    assert any("not travel time" in p for p in ranked["policy"])

    # Red Onion: supply + price are INSUFFICIENT_DATA -> only demand supported.
    ro = client.get("/markets/rank", params={"commodity": "Red Onion", "province": "Rizal"}).json()
    assert ro["supported_analytics"] == 1

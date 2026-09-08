"""Farmer-relative market ranking.

Every weight and policy line comes from
``ml/artifacts/config/market_recommendation_config.json``. The score ranks
curated public markets for one commodity/province against each other; it is a
transparent heuristic, not a routing engine and not measured demand.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from markets.registry import MarketRecord, MarketRegistry

_DEFAULT_COMPONENTS = {
    "proximity": {"weight": 0.4},
    "market_size_proxy": {"weight": 0.25},
    "data_reliability": {"weight": 0.2},
    "commodity_analytics_support": {"weight": 0.15},
}


@dataclass(frozen=True)
class RankedMarket:
    market: MarketRecord
    score: float
    distance_km: float
    breakdown: dict = field(default_factory=dict)
    why: str = ""


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _size_proxy(market_type: str | None, config: dict) -> float:
    keywords: dict = config.get("market_size_proxy_keywords", {})
    default = float(keywords.get("default", 0.55))
    if not market_type:
        return default
    lowered = market_type.lower()
    for keyword, value in keywords.items():
        if keyword != "default" and keyword in lowered:
            return float(value)
    return default


def _reliability(confidence: str, config: dict) -> float:
    table: dict = config.get("coordinate_confidence_score", {})
    return float(table.get(confidence, table.get("default", 0.25)))


def rank_markets(
    registry: MarketRegistry,
    *,
    province: str,
    supported_analytics: int,
    limit: int = 10,
) -> list[RankedMarket]:
    """`supported_analytics`: how many of demand/supply/price are available for
    the commodity (0-3) — feeds ``commodity_analytics_support``."""
    config = registry.config or {}
    components = config.get("components") or _DEFAULT_COMPONENTS
    weights = {k: float(v.get("weight", 0.0)) for k, v in components.items()}
    total = sum(weights.values()) or 1.0
    weights = {k: v / total for k, v in weights.items()}

    origin = registry.province_centroid(province)
    candidates = registry.for_province(province)
    if not candidates or origin is None:
        return []

    rows = []
    for market in candidates:
        distance = _haversine_km(origin, (market.latitude, market.longitude))
        rows.append((market, distance))

    max_distance = max(d for _, d in rows) or 1.0
    analytics_score = supported_analytics / 3.0

    ranked: list[RankedMarket] = []
    for market, distance in rows:
        parts = {
            "proximity": round(1.0 - distance / max_distance, 4),
            "market_size_proxy": round(_size_proxy(market.market_type, config), 4),
            "data_reliability": round(_reliability(market.coordinate_confidence, config), 4),
            "commodity_analytics_support": round(analytics_score, 4),
        }
        score = round(
            100.0 * sum(weights.get(k, 0.0) * v for k, v in parts.items()), 2
        )
        ranked.append(
            RankedMarket(
                market=market,
                score=score,
                distance_km=round(distance, 1),
                breakdown={
                    k: {"score": parts[k], "weight": round(weights.get(k, 0.0), 4)}
                    for k in parts
                },
                why=_why(market, distance, parts),
            )
        )

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:limit]


def _why(market: MarketRecord, distance: float, parts: dict) -> str:
    bits = [f"~{distance:.0f} km from the province centre (straight line, not travel time)"]
    if parts["market_size_proxy"] >= 0.8:
        bits.append("large market type")
    if market.coordinate_confidence in {"HIGH", "MEDIUM"}:
        bits.append(f"{market.coordinate_confidence.lower()}-confidence location")
    else:
        bits.append("location needs verification")
    return "; ".join(bits)

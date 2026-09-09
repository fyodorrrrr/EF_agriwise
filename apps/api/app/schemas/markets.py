"""Curated-market contract schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.forecast import Commodity, Province


class MarketRecord(BaseModel):
    market_id: str
    market_name: str
    municipality: str
    province: Province
    latitude: float
    longitude: float
    market_type: str | None = None
    operator: str | None = None
    coordinate_confidence: str
    source_url: str | None = None
    notes: str | None = None


class MarketListResponse(BaseModel):
    markets: list[MarketRecord]
    diagnostics: list[str] = Field(default_factory=list)


class RankedMarket(BaseModel):
    market: MarketRecord
    score: float
    distance_km: float
    breakdown: dict = Field(default_factory=dict)
    why: str


class MarketRankingResponse(BaseModel):
    commodity: Commodity
    province: Province
    supported_analytics: int  # 0-3 of demand/supply/price available
    ranked: list[RankedMarket]
    policy: list[str] = Field(default_factory=list)

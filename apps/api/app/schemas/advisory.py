from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.forecast import Commodity, Confidence, Frequency, Province, Verdict

AdvisoryType = Literal["OPPORTUNITY", "MARKET_WATCH", "RISK", "PRICE_UPDATE", "MARKET_ACCESS"]


class AdvisoryComponent(BaseModel):
    value: float | None = None
    unit: str | None = None
    frequency: Frequency | None = None
    verdict: Verdict
    confidence: Confidence | None = None
    source: str | None = None
    limitations: list[str] = Field(default_factory=list)


class AdvisorySignals(BaseModel):
    demand_growth_pct: float | None = None
    supply_growth_pct: float | None = None
    price_growth_pct: float | None = None
    physical_gap: float | None = None
    gap_ratio: float | None = None


class AdvisoryMarket(BaseModel):
    market_id: str
    market_name: str
    municipality: str
    market_type: str | None = None
    coordinate_confidence: str
    distance_km: float


class AdvisoryRecord(BaseModel):
    commodity: Commodity
    province: Province
    period: str | None = None
    advisory_type: AdvisoryType
    priority: int
    headline: str
    summary: str
    farmer_consideration: str
    opportunity: dict
    signals: AdvisorySignals
    demand: AdvisoryComponent
    supply: AdvisoryComponent
    price: AdvisoryComponent
    markets: list[AdvisoryMarket] = Field(default_factory=list)
    confidence: Confidence
    limitations: list[str] = Field(default_factory=list)


class AdvisoryResponse(BaseModel):
    province: Province
    period: str | None = None
    market_brief: dict[str, int]
    advisories: list[AdvisoryRecord]

"""Forecast contract schemas.

`Commodity`/`Province` are hardcoded Literals for FastAPI/Pydantic
validation; `ml/forecasting/domain.py` is the runtime source of truth for
the same values — keep the two in sync by hand.

Deferred to a later sprint — do not add here yet:
  - `data_as_of` reconciliation for the optional rice FIES/XGBoost benchmark
    path (Sprint 3, Task 3.1)
  - `/forecast/methodology` response shape (Sprint 3)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Commodity = Literal["Rice", "Tomato", "Red Onion", "Banana"]
Province = Literal["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
Verdict = Literal[
    "PASS", "CAUTION", "INSUFFICIENT_DATA", "USABLE_PROXY", "INDICATIVE_PROXY"
]
Frequency = Literal["monthly", "quarterly"]
Confidence = Literal["HIGH", "MODERATE", "NONE"]


class CommodityProvincePair(BaseModel):
    commodity: Commodity
    province: Province


class CatalogResponse(BaseModel):
    commodities: list[Commodity]
    provinces: list[Province]
    pairs: list[CommodityProvincePair]


class SeriesPoint(BaseModel):
    period: str  # ISO date, e.g. "2026-01-01"
    value: float


class OutlookComponent(BaseModel):
    verdict: Verdict
    observed: list[SeriesPoint] | None = None  # historical tail, oldest -> newest
    forecast: list[SeriesPoint] | None = None  # up to 4 future periods
    unit: str | None = None
    frequency: Frequency | None = None
    confidence: Confidence | None = None
    source: str | None = None
    data_as_of: str | None = None  # last observed period
    label: str | None = None  # demand only, e.g. "Cereal Household Demand Proxy"
    limitations: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class OpportunityComponent(BaseModel):
    verdict: Verdict
    score: float | None = None
    classification: str | None = None
    shared_quarter: str | None = None  # ISO date of the quarter scored
    breakdown: dict = Field(default_factory=dict)  # per-component raw/score/weight
    weights_used: dict = Field(default_factory=dict)  # renormalized weights


class OutlookResponse(BaseModel):
    commodity: Commodity
    province: Province
    resolution_note: str
    demand: OutlookComponent
    supply: OutlookComponent
    price: OutlookComponent
    opportunity: OpportunityComponent


class EvidenceComponent(BaseModel):
    commodity: Commodity
    component: Literal["demand", "supply", "price"]
    target: str | None = None  # e.g. "BREAD", "PSA volume of production"
    model: str | None = None  # selected_model / strategy; None when unavailable
    verdict: Verdict
    reason: str | None = None
    frequency: Frequency | None = None
    province_resolution: str = "province"
    source: str | None = None
    schema_version: str | None = None
    metrics: dict = Field(default_factory=dict)
    baseline: dict = Field(default_factory=dict)  # seasonal-naive baseline where present
    province_holdout: list[dict] = Field(default_factory=list)  # demand only
    limitations: list[str] = Field(default_factory=list)


class EvidenceResponse(BaseModel):
    components: list[EvidenceComponent]


class MethodologyResponse(BaseModel):
    schema_version: str | None = None
    demand: dict = Field(default_factory=dict)
    supply: dict = Field(default_factory=dict)
    price: dict = Field(default_factory=dict)
    opportunity: dict = Field(default_factory=dict)  # opportunity_scoring_config.json
    commodity_flow: dict = Field(default_factory=dict)
    disclaimers: list[str] = Field(default_factory=list)

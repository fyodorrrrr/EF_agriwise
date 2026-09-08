"""Forecast contract schemas.

Deferred to a later sprint — do not add here yet:
  - a `demand_label` field enforcing "Estimated Demand Proxy" wording (no
    demand values are produced in Sprint 1, so there's nothing to label yet)
  - `data_as_of` format reconciliation (date vs. year string, for the future
    rice FIES/XGBoost benchmark path)
  - `/forecast/evidence` and `/forecast/methodology` response shapes

`Commodity`/`Province` are hardcoded Literals for FastAPI/Pydantic
validation; `ml/forecasting/domain.py` is the runtime source of truth for
the same values — keep the two in sync by hand.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Commodity = Literal["Rice", "Tomato", "Red Onion", "Banana"]
Province = Literal["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
Verdict = Literal["PASS", "CAUTION", "INSUFFICIENT_DATA", "USABLE_PROXY"]
Frequency = Literal["monthly", "quarterly"]
Confidence = Literal["HIGH", "MODERATE", "NONE"]


class CommodityProvincePair(BaseModel):
    commodity: Commodity
    province: Province


class CatalogResponse(BaseModel):
    commodities: list[Commodity]
    provinces: list[Province]
    pairs: list[CommodityProvincePair]


class OutlookComponent(BaseModel):
    verdict: Verdict
    values: list[float] | None = None
    unit: str | None = None
    frequency: Frequency | None = None
    confidence: Confidence | None = None
    source: str | None = None
    data_as_of: str | None = None
    limitations: list[str] = Field(default_factory=list)


class OpportunityComponent(BaseModel):
    verdict: Verdict
    score: float | None = None
    classification: str | None = None


class OutlookResponse(BaseModel):
    commodity: Commodity
    province: Province
    resolution_note: str
    demand: OutlookComponent
    supply: OutlookComponent
    price: OutlookComponent
    opportunity: OpportunityComponent

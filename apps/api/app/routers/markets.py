from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.forecast import Commodity, Province
from app.schemas.markets import (
    MarketListResponse,
    MarketRankingResponse,
    MarketRecord,
    RankedMarket,
)
from markets.ranking import rank_markets
from markets.registry import MarketRegistry
from ml.forecasting.forecast_service import ForecastService

router = APIRouter(prefix="/markets", tags=["markets"])


def get_market_registry(request: Request) -> MarketRegistry:
    registry = getattr(request.app.state, "market_registry", None)
    if registry is None:
        raise HTTPException(status_code=500, detail="market registry not initialized")
    return registry


def get_forecast_service(request: Request) -> ForecastService:
    service = getattr(request.app.state, "forecast_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="forecast service not initialized")
    return service


def _record(m) -> MarketRecord:
    return MarketRecord(
        market_id=m.market_id,
        market_name=m.market_name,
        municipality=m.municipality,
        province=m.province,
        latitude=m.latitude,
        longitude=m.longitude,
        market_type=m.market_type,
        operator=m.operator,
        coordinate_confidence=m.coordinate_confidence,
        source_url=m.source_url,
        notes=m.notes,
    )


@router.get("", response_model=MarketListResponse)
def list_markets(
    registry: Annotated[MarketRegistry, Depends(get_market_registry)],
    province: Province | None = None,
) -> MarketListResponse:
    markets = registry.for_province(province) if province else list(registry.markets)
    return MarketListResponse(
        markets=[_record(m) for m in markets],
        diagnostics=list(registry.diagnostics),
    )


@router.get("/rank", response_model=MarketRankingResponse)
def rank(
    commodity: Commodity,
    province: Province,
    registry: Annotated[MarketRegistry, Depends(get_market_registry)],
    forecast: Annotated[ForecastService, Depends(get_forecast_service)],
) -> MarketRankingResponse:
    outlook = forecast.outlook(commodity, province)
    supported = sum(
        1
        for component in (outlook.demand, outlook.supply, outlook.price)
        if component.verdict != "INSUFFICIENT_DATA"
    )
    ranked = rank_markets(registry, province=province, supported_analytics=supported)
    return MarketRankingResponse(
        commodity=commodity,
        province=province,
        supported_analytics=supported,
        ranked=[
            RankedMarket(
                market=_record(r.market),
                score=r.score,
                distance_km=r.distance_km,
                breakdown=r.breakdown,
                why=r.why,
            )
            for r in ranked
        ],
        policy=list((registry.config or {}).get("policy", [])),
    )

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.forecast import (
    CatalogResponse,
    Commodity,
    CommodityProvincePair,
    OpportunityComponent,
    OutlookComponent,
    OutlookResponse,
    Province,
)
from ml.forecasting.forecast_service import ForecastService

router = APIRouter(prefix="/forecast", tags=["forecast"])


def get_forecast_service(request: Request) -> ForecastService:
    # Unlike RAG's `get_pipeline`, this does not 503 in normal operation: an
    # empty-registry service is still valid and answers INSUFFICIENT_DATA.
    # This defensive branch only guards against `app.state.forecast_service`
    # never having been set, which should not happen — `main.py` always
    # constructs a real service, even with zero artifacts.
    service = getattr(request.app.state, "forecast_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="forecast service not initialized")
    return service


@router.get("/catalog", response_model=CatalogResponse)
def catalog(
    service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> CatalogResponse:
    payload = service.catalog()
    return CatalogResponse(
        commodities=list(payload.commodities),
        provinces=list(payload.provinces),
        pairs=[
            CommodityProvincePair(commodity=pair.commodity, province=pair.province)
            for pair in payload.pairs
        ],
    )


@router.get("/outlook", response_model=OutlookResponse)
def outlook(
    commodity: Commodity,
    province: Province,
    service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> OutlookResponse:
    payload = service.outlook(commodity, province)
    return OutlookResponse(
        commodity=payload.commodity,
        province=payload.province,
        resolution_note=payload.resolution_note,
        demand=OutlookComponent(**payload.demand.__dict__),
        supply=OutlookComponent(**payload.supply.__dict__),
        price=OutlookComponent(**payload.price.__dict__),
        opportunity=OpportunityComponent(**payload.opportunity.__dict__),
    )

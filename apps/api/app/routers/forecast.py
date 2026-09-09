from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.forecast import (
    CatalogResponse,
    Commodity,
    CommodityProvincePair,
    EvidenceComponent,
    EvidenceResponse,
    MethodologyResponse,
    MunicipalOutlookRecord,
    MunicipalOutlookResponse,
    OpportunityComponent,
    OutlookComponent,
    OutlookResponse,
    Province,
)
from ml.forecasting.forecast_service import ForecastService
from ml.forecasting.municipal_disaggregation import MunicipalDisaggregationService

router = APIRouter(prefix="/forecast", tags=["forecast"])


def get_forecast_service(request: Request) -> ForecastService:
    service = getattr(request.app.state, "forecast_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="forecast service not initialized")
    return service


def get_municipal_disaggregation_service(request: Request) -> MunicipalDisaggregationService:
    service = getattr(request.app.state, "municipal_disaggregation_service", None)
    if service is None:
        raise HTTPException(
            status_code=500, detail="municipal disaggregation service not initialized"
        )
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


@router.get("/municipal-outlook", response_model=MunicipalOutlookResponse)
def municipal_outlook(
    commodity: Commodity,
    province: Province,
    service: Annotated[
        MunicipalDisaggregationService, Depends(get_municipal_disaggregation_service)
    ],
) -> MunicipalOutlookResponse:
    payload = service.outlook(commodity, province)
    return MunicipalOutlookResponse(
        province=payload.province,
        commodity=payload.commodity,
        methodology=payload.methodology,
        demand_unit=payload.demand_unit,
        supply_unit=payload.supply_unit,
        municipalities=[MunicipalOutlookRecord(**item) for item in payload.municipalities],
    )


@router.get("/evidence", response_model=EvidenceResponse)
def evidence(
    service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> EvidenceResponse:
    return EvidenceResponse(
        components=[EvidenceComponent(**item.__dict__) for item in service.evidence()]
    )


@router.get("/methodology", response_model=MethodologyResponse)
def methodology(
    service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> MethodologyResponse:
    return MethodologyResponse(**service.methodology().__dict__)

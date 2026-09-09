from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.advisory import AdvisoryResponse
from app.schemas.forecast import Province
from ml.forecasting.advisory import AdvisoryService

router = APIRouter(prefix="/advisory", tags=["advisory"])


def get_advisory_service(request: Request) -> AdvisoryService:
    service = getattr(request.app.state, "advisory_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="advisory service not initialized")
    return service


@router.get("", response_model=AdvisoryResponse)
def advisory(
    province: Province, service: Annotated[AdvisoryService, Depends(get_advisory_service)]
) -> AdvisoryResponse:
    return AdvisoryResponse(**service.advisories(province))

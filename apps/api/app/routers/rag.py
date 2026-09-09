from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.entities import extract_entities, wants_overview
from app.rag_context import build_analytics_context, build_full_grid_context
from app.schemas.rag import Citation, RagQueryRequest, RagQueryResponse
from ml.forecasting.domain import COMMODITIES, PROVINCES
from ml.forecasting.forecast_service import ForecastService
from rag.generator import RagGenerationError
from rag.pipeline import RagPipeline
from rag.prompt import ChatTurn

router = APIRouter(prefix="/rag", tags=["rag"])


def get_pipeline(request: Request) -> RagPipeline:
    pipeline = getattr(request.app.state, "rag_pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline unavailable; run `uv run python -m rag.ingest` to build the index",
        )
    return pipeline


def get_forecast_service(request: Request) -> ForecastService | None:
    return getattr(request.app.state, "forecast_service", None)


@router.post("/query", response_model=RagQueryResponse)
def query(
    payload: RagQueryRequest,
    pipeline: Annotated[RagPipeline, Depends(get_pipeline)],
    forecast: Annotated[ForecastService | None, Depends(get_forecast_service)],
) -> RagQueryResponse:
    if not pipeline.can_generate:
        raise HTTPException(
            status_code=503,
            detail="generation unavailable: GROQ_API_KEY not configured",
        )
    history = [ChatTurn(role=m.role, content=m.content) for m in payload.history]

    # What the question names wins; the dropdown selectors are only a fallback for
    # the parts the question leaves unsaid. Bogus selectors are dropped.
    found_commodity, found_province = extract_entities(payload.question)
    commodity = found_commodity or payload.commodity
    province = found_province or payload.province
    commodity = commodity if commodity in COMMODITIES else None
    province = province if province in PROVINCES else None

    analytics_context = None
    analytics_scope = None
    if forecast is not None and (commodity or province or wants_overview(payload.question)):
        grid = build_full_grid_context(forecast)
        if grid:
            blocks: list[str] = []
            if commodity and province:
                focused = build_analytics_context(forecast, commodity, province)
                if focused:
                    blocks.append(
                        f"Focused view for the question — {commodity} in {province}:\n{focused}"
                    )
                    analytics_scope = f"{commodity} · {province}"
            blocks.append(grid)
            analytics_context = "\n\n".join(blocks)
            if analytics_scope is None:
                analytics_scope = (
                    f"{commodity} · all provinces"
                    if commodity
                    else f"{province} · all commodities"
                    if province
                    else "CALABARZON overview"
                )

    try:
        result = pipeline.answer(payload.question, history, analytics_context=analytics_context)
    except RagGenerationError as exc:
        raise HTTPException(status_code=503, detail=f"generation failed: {exc}") from exc
    return RagQueryResponse(
        answer=result.answer,
        citations=[Citation(**citation.model_dump()) for citation in result.citations],
        analytics_context_used=analytics_context is not None,
        analytics_scope=analytics_scope,
    )

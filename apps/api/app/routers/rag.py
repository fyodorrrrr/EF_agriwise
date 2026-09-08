from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.rag_context import build_analytics_context
from app.schemas.rag import Citation, RagQueryRequest, RagQueryResponse
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

    analytics_context = None
    if forecast is not None:
        analytics_context = build_analytics_context(
            forecast, payload.commodity, payload.province
        )

    try:
        result = pipeline.answer(payload.question, history, analytics_context=analytics_context)
    except RagGenerationError as exc:
        raise HTTPException(status_code=503, detail=f"generation failed: {exc}") from exc
    return RagQueryResponse(
        answer=result.answer,
        citations=[Citation(**citation.model_dump()) for citation in result.citations],
        analytics_context_used=analytics_context is not None,
    )

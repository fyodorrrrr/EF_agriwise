from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.contacts import find_contact, municipality_in
from app.entities import extract_entities, wants_contact, wants_markets, wants_overview
from app.rag_context import (
    build_analytics_context,
    build_full_grid_context,
    build_markets_context,
)
from app.schemas.rag import Citation, RagQueryRequest, RagQueryResponse
from ml.forecasting.domain import COMMODITIES, PROVINCES
from ml.forecasting.forecast_service import ForecastService
from rag.generator import RagGenerationError
from rag.pipeline import OUT_OF_SCOPE_ANSWER, RagPipeline, _is_smalltalk
from rag.prompt import ChatTurn

# Phrases the model uses (per the system prompt) when it is handing the farmer
# off to a person rather than answering from the manuals or the analytics.
_HANDOFF_MARKERS = (
    "municipal agricultur",
    "provincial agricultur",
    "department of agriculture",
    "municipal agriculture office",
    "local da office",
)

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


def get_market_registry(request: Request):
    return getattr(request.app.state, "market_registry", None)


@router.post("/query", response_model=RagQueryResponse)
def query(
    payload: RagQueryRequest,
    pipeline: Annotated[RagPipeline, Depends(get_pipeline)],
    forecast: Annotated[ForecastService | None, Depends(get_forecast_service)],
    market_registry: Annotated[object, Depends(get_market_registry)] = None,
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

    markets_intent = wants_markets(payload.question)
    overview_intent = wants_overview(payload.question)

    analytics_context = None
    analytics_scope = None
    if forecast is not None and (commodity or province or overview_intent):
        blocks: list[str] = []

        # Where-to-sell question with a known province → market ranking.
        if markets_intent and province:
            markets = build_markets_context(market_registry, forecast, province, commodity)
            if markets:
                blocks.append(markets)

        # Commodity + province → the precise per-quarter outlook for that pair.
        # Otherwise → the compact grid so cross-cutting questions still resolve.
        if commodity and province:
            focused = build_analytics_context(forecast, commodity, province)
            if focused:
                blocks.append(focused)
        else:
            grid = build_full_grid_context(forecast)
            if grid:
                blocks.append(grid)

        if blocks:
            analytics_context = "\n\n".join(blocks)
            if markets_intent and province:
                analytics_scope = f"{province} markets" + (
                    f" · {commodity}" if commodity else ""
                )
            elif commodity and province:
                analytics_scope = f"{commodity} · {province}"
            elif commodity:
                analytics_scope = f"{commodity} · all provinces"
            elif province:
                analytics_scope = f"{province} · all commodities"
            else:
                analytics_scope = "CALABARZON overview"

    try:
        result = pipeline.answer(payload.question, history, analytics_context=analytics_context)
    except RagGenerationError as exc:
        raise HTTPException(status_code=503, detail=f"generation failed: {exc}") from exc

    # Hand the farmer a real office to reach when the bot couldn't fully help
    # (answered from neither the manuals nor the analytics and is deferring), or
    # when they explicitly asked for a contact.
    contact = None
    asked_for_contact = wants_contact(payload.question)
    deferred = (
        result.answer != OUT_OF_SCOPE_ANSWER
        and not result.citations
        and not _is_smalltalk(payload.question)
        and any(marker in result.answer.lower() for marker in _HANDOFF_MARKERS)
    )
    if asked_for_contact or deferred:
        contact = find_contact(province, municipality_in(payload.question))

    return RagQueryResponse(
        answer=result.answer,
        citations=[Citation(**citation.model_dump()) for citation in result.citations],
        analytics_context_used=analytics_context is not None,
        analytics_scope=analytics_scope,
        contact=contact,
    )

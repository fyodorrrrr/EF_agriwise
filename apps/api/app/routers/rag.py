from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.rag import Citation, RagQueryRequest, RagQueryResponse
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


@router.post("/query", response_model=RagQueryResponse)
def query(
    payload: RagQueryRequest,
    pipeline: Annotated[RagPipeline, Depends(get_pipeline)],
) -> RagQueryResponse:
    if not pipeline.can_generate:
        raise HTTPException(
            status_code=503,
            detail="generation unavailable: GROQ_API_KEY not configured",
        )
    history = [ChatTurn(role=m.role, content=m.content) for m in payload.history]
    try:
        result = pipeline.answer(payload.question, history)
    except RagGenerationError as exc:
        raise HTTPException(status_code=503, detail=f"generation failed: {exc}") from exc
    return RagQueryResponse(
        answer=result.answer,
        citations=[Citation(**citation.model_dump()) for citation in result.citations],
    )

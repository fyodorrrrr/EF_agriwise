from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

if TYPE_CHECKING:
    from app.config import Settings
    from rag.pipeline import RagPipeline

logger = logging.getLogger("agriwise.rag")


def _build_rag_pipeline(settings: Settings) -> RagPipeline | None:
    from app.config import build_rag_config

    manifest_path = Path(settings.rag_index_dir) / "manifest.json"
    if not manifest_path.exists():
        logger.warning(
            "RAG index missing at %s; /rag/query returns 503. Run `uv run python -m rag.ingest`.",
            manifest_path.parent,
        )
        return None
    try:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("embedding_model") != settings.embedding_model:
            logger.warning(
                "RAG index embedding model %r != configured %r; rebuild with --rebuild.",
                manifest.get("embedding_model"),
                settings.embedding_model,
            )
        from rag.pipeline import RagPipeline

        pipeline = RagPipeline.from_config(build_rag_config(settings))
        pipeline.warmup()
        return pipeline
    except Exception:
        logger.exception("failed to build RAG pipeline; /rag/query returns 503")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook.

    The forecasting artifact registry and RAG retriever are loaded once here
    and attached to `app.state` so requests reuse a single cached instance.
    """
    app.state.rag_pipeline = _build_rag_pipeline(get_settings())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    from app.routers import rag as rag_router

    app.include_router(rag_router.router)

    # Ensure the attribute exists even when TestClient is used without the
    # lifespan context manager. The lifespan value wins when the app runs
    # normally or under `with TestClient(...)`.
    app.state.rag_pipeline = None

    return app


app = create_app()

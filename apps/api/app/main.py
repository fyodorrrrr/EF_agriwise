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
    from ml.forecasting.forecast_service import ForecastService
    from rag.pipeline import RagPipeline

logger = logging.getLogger("agriwise.rag")
forecast_logger = logging.getLogger("agriwise.forecast")


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


def _build_forecast_service(settings: Settings) -> ForecastService:
    """Build the forecast service from the cached artifact registry.

    Unlike `_build_rag_pipeline`, this cannot fail into `None`: an empty
    registry (no artifacts present) is still a valid service that answers
    every `/forecast/outlook` component with INSUFFICIENT_DATA, so
    `/forecast/*` never 503s the way `/rag/query` does on a missing index.
    """
    from pathlib import Path

    from ml.forecasting.artifact_registry import ArtifactRegistry
    from ml.forecasting.forecast_service import ForecastService

    artifacts_dir = Path(settings.forecast_artifacts_dir)
    try:
        registry = ArtifactRegistry.load(artifacts_dir)
    except Exception:
        # Should be unreachable — ArtifactRegistry.load never raises — but
        # fall back to an explicit empty registry rather than let startup fail.
        forecast_logger.exception(
            "unexpected error loading forecast artifacts from %s; using empty registry",
            artifacts_dir,
        )
        registry = ArtifactRegistry(artifacts_dir)
    return ForecastService(registry)


def _build_market_registry(settings: Settings):
    from markets.registry import MarketRegistry

    artifacts_dir = Path(settings.forecast_artifacts_dir)
    try:
        return MarketRegistry.load(artifacts_dir)
    except Exception:
        forecast_logger.exception(
            "unexpected error loading market registry from %s; using empty registry",
            artifacts_dir,
        )
        return MarketRegistry(markets=(), config={})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook.

    The forecasting artifact registry, market registry, and RAG retriever are
    loaded once here and attached to `app.state` so requests reuse a single
    cached instance.
    """
    app.state.rag_pipeline = _build_rag_pipeline(get_settings())
    app.state.forecast_service = _build_forecast_service(get_settings())
    app.state.market_registry = _build_market_registry(get_settings())
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

    from app.routers import forecast as forecast_router
    from app.routers import markets as markets_router
    from app.routers import rag as rag_router

    app.include_router(rag_router.router)
    app.include_router(forecast_router.router)
    app.include_router(markets_router.router)

    # Ensure these attributes exist even when TestClient is used without the
    # lifespan context manager. The lifespan values win when the app runs
    # normally or under `with TestClient(...)`.
    app.state.rag_pipeline = None
    app.state.forecast_service = _build_forecast_service(settings)
    app.state.market_registry = _build_market_registry(settings)

    return app


app = create_app()

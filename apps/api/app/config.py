from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from rag.config import RagConfig

# apps/api/app/config.py -> parents[0]=app, [1]=api, [2]=apps, [3]=repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / "apps/api/.env", _REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AgriWise API"
    debug: bool = False

    # Comma-separated list of allowed browser origins for CORS.
    cors_origins: str = "http://localhost:3000"

    # Generation LLM (RAG). GROQ_API_KEY is optional; /rag/query returns 503 without it.
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    # RAG retrieval / ingestion
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 4
    rag_index_dir: str = "data/processed/rag_index"
    rag_score_floor: float = 0.0

    # Forecast artifact registry. Missing/empty directory is a valid state:
    # the registry loads empty and every component reports INSUFFICIENT_DATA.
    forecast_artifacts_dir: str = "ml/artifacts"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def build_rag_config(settings: Settings) -> RagConfig:
    from pathlib import Path

    from rag.config import RagConfig

    return RagConfig(
        groq_api_key=settings.groq_api_key,
        groq_model=settings.groq_model,
        embedding_model=settings.embedding_model,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        top_k=settings.rag_top_k,
        index_dir=Path(settings.rag_index_dir),
        score_floor=settings.rag_score_floor,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

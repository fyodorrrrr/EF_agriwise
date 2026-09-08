from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_INDEX_DIR = Path("data/processed/rag_index")


@dataclass(frozen=True)
class RagConfig:
    """Immutable RAG pipeline configuration.

    ``chunk_size`` and ``chunk_overlap`` are measured in characters, never tokens.
    """

    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4
    index_dir: Path = field(default=DEFAULT_INDEX_DIR)
    score_floor: float = 0.0
    collection_name: str = "agriwise_docs"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> RagConfig:
        """Build a config from environment variables, falling back to defaults."""
        env = os.environ if environ is None else environ
        defaults = cls()
        return cls(
            groq_api_key=env.get("GROQ_API_KEY") or None,
            groq_model=env.get("GROQ_MODEL", defaults.groq_model),
            embedding_model=env.get("EMBEDDING_MODEL", defaults.embedding_model),
            chunk_size=int(env.get("RAG_CHUNK_SIZE", defaults.chunk_size)),
            chunk_overlap=int(env.get("RAG_CHUNK_OVERLAP", defaults.chunk_overlap)),
            top_k=int(env.get("RAG_TOP_K", defaults.top_k)),
            index_dir=Path(env.get("RAG_INDEX_DIR", str(defaults.index_dir))),
            score_floor=float(env.get("RAG_SCORE_FLOOR", defaults.score_floor)),
        )

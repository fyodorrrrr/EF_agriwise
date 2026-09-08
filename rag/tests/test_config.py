from __future__ import annotations

from pathlib import Path

from rag.config import RagConfig


def test_defaults_match_spec():
    cfg = RagConfig()
    assert cfg.groq_model == "openai/gpt-oss-120b"
    assert cfg.embedding_model == "all-MiniLM-L6-v2"
    assert cfg.chunk_size == 500
    assert cfg.chunk_overlap == 50
    assert cfg.top_k == 4
    assert cfg.index_dir == Path("data/processed/rag_index")
    assert cfg.score_floor == 0.0
    assert cfg.collection_name == "agriwise_docs"
    assert cfg.groq_api_key is None


def test_from_env_overrides_and_types():
    cfg = RagConfig.from_env(
        {
            "GROQ_API_KEY": "sk-test",
            "RAG_CHUNK_SIZE": "800",
            "RAG_TOP_K": "6",
            "RAG_SCORE_FLOOR": "0.25",
            "RAG_INDEX_DIR": "/tmp/idx",
        }
    )
    assert cfg.groq_api_key == "sk-test"
    assert cfg.chunk_size == 800
    assert cfg.top_k == 6
    assert cfg.score_floor == 0.25
    assert cfg.index_dir == Path("/tmp/idx")
    # untouched keys keep defaults
    assert cfg.groq_model == "openai/gpt-oss-120b"


def test_from_env_blank_api_key_is_none():
    assert RagConfig.from_env({"GROQ_API_KEY": ""}).groq_api_key is None

from __future__ import annotations

import json

from app.config import Settings
from app.main import _build_rag_pipeline


def _settings(index_dir) -> Settings:
    return Settings(rag_index_dir=str(index_dir))


def _write_manifest(index_dir, embedding_model: str = "all-MiniLM-L6-v2") -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "manifest.json").write_text(
        json.dumps({"embedding_model": embedding_model, "documents": {}})
    )


def test_missing_manifest_returns_none(tmp_path):
    assert _build_rag_pipeline(_settings(tmp_path / "idx")) is None


def test_from_config_raising_returns_none(tmp_path, monkeypatch):
    index_dir = tmp_path / "idx"
    _write_manifest(index_dir)

    def _boom(_cfg):
        raise RuntimeError("store unavailable")

    monkeypatch.setattr("rag.pipeline.RagPipeline.from_config", staticmethod(_boom))
    assert _build_rag_pipeline(_settings(index_dir)) is None


def test_mismatched_embedding_model_logs_warning_and_builds(tmp_path, monkeypatch, caplog):
    index_dir = tmp_path / "idx"
    _write_manifest(index_dir, embedding_model="some-other-model")

    class _Dummy:
        def warmup(self) -> None:
            pass

    dummy = _Dummy()
    monkeypatch.setattr(
        "rag.pipeline.RagPipeline.from_config", staticmethod(lambda _cfg: dummy)
    )
    with caplog.at_level("WARNING", logger="agriwise.rag"):
        result = _build_rag_pipeline(_settings(index_dir))

    assert result is dummy
    assert any("embedding model" in r.getMessage() for r in caplog.records)


def test_valid_manifest_builds_and_warms_up(tmp_path, monkeypatch):
    index_dir = tmp_path / "idx"
    _write_manifest(index_dir)

    calls: list[str] = []

    class _Dummy:
        def warmup(self) -> None:
            calls.append("warmup")

    monkeypatch.setattr(
        "rag.pipeline.RagPipeline.from_config", staticmethod(lambda _cfg: _Dummy())
    )
    result = _build_rag_pipeline(_settings(index_dir))
    assert isinstance(result, _Dummy)
    assert calls == ["warmup"]

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routers.rag import get_pipeline
from rag.generator import RagGenerationError
from rag.pipeline import Citation, RagAnswer


class _StubPipeline:
    def __init__(self, *, can_generate=True, answer=None, raises=None):
        self.can_generate = can_generate
        self._answer = answer
        self._raises = raises
        self.calls: list[tuple[str, int]] = []

    def answer(self, question, history=None, analytics_context=None):
        self.calls.append((question, len(history or [])))
        self.last_analytics_context = analytics_context
        if self._raises:
            raise self._raises
        return self._answer


def _client(pipeline) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_pipeline] = lambda: pipeline
    return TestClient(app)


def test_query_returns_answer_and_citations():
    answer = RagAnswer(
        answer="Use a cash book.",
        citations=[Citation(doc_id="fbs", doc_title="Farm Business School Manual",
                            page_start=88, page_end=89)],
        used_chunk_ids=["fbs::3"],
    )
    client = _client(_StubPipeline(answer=answer))
    resp = client.post("/rag/query", json={"question": "how to record expenses"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Use a cash book."
    assert body["citations"][0]["doc_title"] == "Farm Business School Manual"
    assert "used_chunk_ids" not in body


def test_query_injects_resolved_analytics_context_from_selectors():
    pipeline = _StubPipeline(
        answer=RagAnswer(answer="ok", citations=[], used_chunk_ids=[])
    )
    client = _client(pipeline)

    resp = client.post(
        "/rag/query",
        json={"question": "how is rice doing?", "commodity": "Rice", "province": "Laguna"},
    )

    body = resp.json()
    if not body["analytics_context_used"]:
        pytest.skip("forecast artifacts not present in this checkout")
    ctx = pipeline.last_analytics_context
    assert "Rice in Laguna province" in ctx
    assert "Estimated Demand Proxy" in ctx
    # A bogus selector is ignored, not trusted.
    resp2 = client.post(
        "/rag/query", json={"question": "q", "commodity": "Gold", "province": "Laguna"}
    )
    assert resp2.json()["analytics_context_used"] is False


def test_query_validation_error_is_422():
    client = _client(_StubPipeline(answer=None))
    assert client.post("/rag/query", json={"question": ""}).status_code == 422
    assert client.post("/rag/query", json={
        "question": "ok",
        "history": [{"role": "user", "content": "x" * 5000}],
    }).status_code == 422


def test_query_503_when_generation_unavailable():
    client = _client(_StubPipeline(can_generate=False))
    resp = client.post("/rag/query", json={"question": "hello"})
    assert resp.status_code == 503
    assert "GROQ_API_KEY" in resp.json()["detail"]


def test_query_503_when_groq_fails():
    client = _client(_StubPipeline(raises=RagGenerationError("groq timeout")))
    resp = client.post("/rag/query", json={"question": "hello"})
    assert resp.status_code == 503
    assert "groq timeout" in resp.json()["detail"]


def test_query_503_when_pipeline_missing():
    # Deterministic: no lifespan (plain TestClient, no `with`), pipeline forced None.
    # This avoids depending on whether data/processed/rag_index/manifest.json exists
    # on the dev/CI machine.
    app = create_app()
    app.state.rag_pipeline = None
    client = TestClient(app)
    assert client.post("/rag/query", json={"question": "hello"}).status_code == 503

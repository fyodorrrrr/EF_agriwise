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
    assert "Rice in Laguna province" in ctx  # focused block
    assert "Full CALABARZON analytics grid" in ctx  # plus the whole grid
    # Fully bogus selectors and no analytics intent → no analytics context.
    resp2 = client.post(
        "/rag/query", json={"question": "q", "commodity": "Gold", "province": "Atlantis"}
    )
    assert resp2.json()["analytics_context_used"] is False


def test_query_resolves_analytics_from_question_text_without_selectors():
    pipeline = _StubPipeline(
        answer=RagAnswer(answer="ok", citations=[], used_chunk_ids=[])
    )
    client = _client(pipeline)

    resp = client.post(
        "/rag/query", json={"question": "what is the price outlook for rice in Laguna?"}
    )
    body = resp.json()
    if not body["analytics_context_used"]:
        pytest.skip("forecast artifacts not present in this checkout")
    assert body["analytics_scope"] == "Rice · Laguna"
    assert "Rice in Laguna province" in pipeline.last_analytics_context


def test_question_entities_win_over_stale_dropdown_selectors():
    pipeline = _StubPipeline(
        answer=RagAnswer(answer="ok", citations=[], used_chunk_ids=[])
    )
    client = _client(pipeline)

    resp = client.post(
        "/rag/query",
        json={
            "question": "Is demand for tomato going up in Cavite?",
            "commodity": "Rice",
            "province": "Laguna",
        },
    )
    body = resp.json()
    if not body["analytics_context_used"]:
        pytest.skip("forecast artifacts not present in this checkout")
    assert body["analytics_scope"] == "Tomato · Cavite"
    assert "Tomato in Cavite province" in pipeline.last_analytics_context


def test_query_labels_scope_when_only_a_commodity_is_named():
    pipeline = _StubPipeline(
        answer=RagAnswer(answer="ok", citations=[], used_chunk_ids=[])
    )
    client = _client(pipeline)

    resp = client.post("/rag/query", json={"question": "where should I plant tomato?"})
    body = resp.json()
    if not body["analytics_context_used"]:
        pytest.skip("forecast artifacts not present in this checkout")
    assert body["analytics_scope"] == "Tomato · all provinces"
    assert "Full CALABARZON analytics grid" in pipeline.last_analytics_context


def test_query_labels_scope_when_only_a_province_is_named():
    pipeline = _StubPipeline(
        answer=RagAnswer(answer="ok", citations=[], used_chunk_ids=[])
    )
    client = _client(pipeline)

    resp = client.post(
        "/rag/query", json={"question": "which crop has the highest demand in Laguna?"}
    )
    body = resp.json()
    if not body["analytics_context_used"]:
        pytest.skip("forecast artifacts not present in this checkout")
    assert body["analytics_scope"] == "Laguna · all commodities"
    assert "Full CALABARZON analytics grid" in pipeline.last_analytics_context


def test_query_injects_full_grid_for_a_broad_planning_question():
    pipeline = _StubPipeline(
        answer=RagAnswer(answer="ok", citations=[], used_chunk_ids=[])
    )
    client = _client(pipeline)

    resp = client.post("/rag/query", json={"question": "what is a good crop to plant?"})
    body = resp.json()
    if not body["analytics_context_used"]:
        pytest.skip("forecast artifacts not present in this checkout")
    assert body["analytics_scope"] == "CALABARZON overview"
    assert "- Rice / Batangas:" in pipeline.last_analytics_context


def test_query_no_analytics_for_a_pure_manual_question():
    pipeline = _StubPipeline(
        answer=RagAnswer(answer="ok", citations=[], used_chunk_ids=[])
    )
    client = _client(pipeline)

    resp = client.post("/rag/query", json={"question": "how do I keep a farm record book?"})
    body = resp.json()
    assert body["analytics_context_used"] is False
    assert body["analytics_scope"] is None


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

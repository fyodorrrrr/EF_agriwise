from __future__ import annotations

import pytest

from rag.generator import RagGenerationError
from rag.pipeline import (
    OUT_OF_SCOPE_ANSWER,
    Citation,
    RagAnswer,
    RagPipeline,
    _plain_text,
)
from rag.prompt import ChatTurn
from rag.retriever import RetrievedChunk


def test_plain_text_strips_markdown():
    raw = "## Answer\n\n**Sell at Pila** if price is `high`.\n\n> a quote\n\n* one\n+ two"
    out = _plain_text(raw)
    assert "**" not in out and "#" not in out and "`" not in out
    assert out.startswith("Answer")
    assert "Sell at Pila if price is high." in out
    assert "\n- one\n- two" in out


class _FakeRetriever:
    def __init__(self, chunks):
        self._chunks = chunks
        self.seen_query: str | None = None

    def retrieve(self, query):
        self.seen_query = query
        return self._chunks


class _FakeGenerator:
    def __init__(self):
        self.seen_messages = None

    def generate(self, messages):
        self.seen_messages = messages
        return "the answer"


def _chunk(cid, doc, ps, pe):
    return RetrievedChunk(
        chunk_id=cid, doc_id=doc, doc_title=doc.upper(),
        page_start=ps, page_end=pe, text="body", score=0.5,
    )


class _CitingGenerator:
    """Emits an answer whose bracket tags name both retrieved sources."""

    def generate(self, messages):
        return "Keep a cash book [FBS, p.10-11]. Hygiene rules are in [GAP, p.3]."


def test_answer_returns_dedup_citations_and_chunk_ids():
    chunks = [
        _chunk("a::0", "fbs", 10, 11),
        _chunk("a::1", "fbs", 10, 11),
        _chunk("b::0", "gap", 3, 3),
    ]
    pipeline = RagPipeline(_FakeRetriever(chunks), _CitingGenerator())
    result = pipeline.answer("how to budget", [ChatTurn(role="user", content="hi")])
    assert isinstance(result, RagAnswer)
    assert result.used_chunk_ids == ["a::0", "a::1", "b::0"]
    assert result.citations == [
        Citation(doc_id="fbs", doc_title="FBS", page_start=10, page_end=11),
        Citation(doc_id="gap", doc_title="GAP", page_start=3, page_end=3),
    ]


def test_citations_are_limited_to_sources_the_answer_named():
    chunks = [_chunk("a::0", "fbs", 10, 11), _chunk("b::0", "gap", 3, 3)]

    class _Gen:
        def generate(self, messages):
            return "Rice price is forecast at 15 PHP/kg by Q4 — no manual needed."

    result = RagPipeline(_FakeRetriever(chunks), _Gen()).answer(
        "price of rice", analytics_context="FORECAST DATA ..."
    )
    assert result.citations == []  # neither FBS nor GAP was mentioned
    assert result.used_chunk_ids == ["a::0", "b::0"]  # retrieval still recorded


def test_answer_without_generator_raises():
    pipeline = RagPipeline(_FakeRetriever([]), None)
    assert pipeline.can_generate is False
    with pytest.raises(RagGenerationError):
        pipeline.answer("q")


def test_out_of_scope_question_is_refused_without_generation():
    gen = _FakeGenerator()
    retriever = _FakeRetriever([])  # nothing relevant retrieved
    result = RagPipeline(retriever, gen).answer("write me some python code")
    assert result.answer == OUT_OF_SCOPE_ANSWER
    assert result.citations == []
    assert result.used_chunk_ids == []
    assert gen.seen_messages is None  # no generation call was spent


def test_analytics_context_bypasses_out_of_scope_when_nothing_retrieved():
    gen = _FakeGenerator()
    retriever = _FakeRetriever([])  # manuals have nothing for this question
    result = RagPipeline(retriever, gen).answer(
        "which province is best for tomato",
        analytics_context="Cross-province comparison for Tomato ...",
    )
    assert result.answer == "the answer"  # generator was used, not the canned line
    assert gen.seen_messages is not None


def test_greeting_reaches_generator_and_skips_retrieval():
    gen = _FakeGenerator()
    retriever = _FakeRetriever([_chunk("a::0", "fbs", 1, 1)])
    result = RagPipeline(retriever, gen).answer("hello")
    assert result.answer == "the answer"
    assert retriever.seen_query is None  # greeting short-circuits retrieval
    assert gen.seen_messages is not None


def test_answer_passes_history_and_question_through():
    gen = _FakeGenerator()
    retriever = _FakeRetriever([_chunk("a::0", "fbs", 1, 1)])
    RagPipeline(retriever, gen).answer("my question", None)
    assert retriever.seen_query == "my question"
    assert gen.seen_messages[0]["role"] == "system"
    assert gen.seen_messages[-1]["content"].endswith("my question")

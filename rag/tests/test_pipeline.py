from __future__ import annotations

import pytest

from rag.generator import RagGenerationError
from rag.pipeline import Citation, RagAnswer, RagPipeline
from rag.prompt import ChatTurn
from rag.retriever import RetrievedChunk


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


def test_answer_returns_dedup_citations_and_chunk_ids():
    chunks = [_chunk("a::0", "fbs", 10, 11), _chunk("a::1", "fbs", 10, 11), _chunk("b::0", "gap", 3, 3)]
    pipeline = RagPipeline(_FakeRetriever(chunks), _FakeGenerator())
    result = pipeline.answer("how to budget", [ChatTurn(role="user", content="hi")])
    assert isinstance(result, RagAnswer)
    assert result.answer == "the answer"
    assert result.used_chunk_ids == ["a::0", "a::1", "b::0"]
    assert result.citations == [
        Citation(doc_id="fbs", doc_title="FBS", page_start=10, page_end=11),
        Citation(doc_id="gap", doc_title="GAP", page_start=3, page_end=3),
    ]


def test_answer_without_generator_raises():
    pipeline = RagPipeline(_FakeRetriever([]), None)
    assert pipeline.can_generate is False
    with pytest.raises(RagGenerationError):
        pipeline.answer("q")


def test_answer_passes_history_and_question_through():
    gen = _FakeGenerator()
    retriever = _FakeRetriever([_chunk("a::0", "fbs", 1, 1)])
    RagPipeline(retriever, gen).answer("my question", None)
    assert retriever.seen_query == "my question"
    assert gen.seen_messages[0]["role"] == "system"
    assert gen.seen_messages[-1]["content"].endswith("my question")

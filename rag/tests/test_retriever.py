from __future__ import annotations

from rag.retriever import RetrievedChunk, Retriever
from rag.store import StoredChunk


class _FakeEmbedder:
    def embed_one(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]


class _FakeStore:
    def __init__(self, chunks: list[StoredChunk]):
        self._chunks = chunks
        self.last_top_k: int | None = None

    def query(self, embedding, top_k):
        self.last_top_k = top_k
        return self._chunks


def _stored(chunk_id: str, score: float) -> StoredChunk:
    return StoredChunk(
        chunk_id=chunk_id,
        text=f"text {chunk_id}",
        metadata={"doc_id": "d", "doc_title": "Doc", "page_start": 3, "page_end": 4},
        score=score,
    )


def test_blank_query_returns_empty():
    r = Retriever(_FakeStore([_stored("a", 0.9)]), _FakeEmbedder(), top_k=4, score_floor=0.0)
    assert r.retrieve("   ") == []


def test_results_sorted_by_score_desc_and_mapped():
    store = _FakeStore([_stored("a", 0.4), _stored("b", 0.8)])
    r = Retriever(store, _FakeEmbedder(), top_k=4, score_floor=0.0)
    out = r.retrieve("how to compost")
    assert [c.chunk_id for c in out] == ["b", "a"]
    assert isinstance(out[0], RetrievedChunk)
    assert out[0].doc_title == "Doc" and out[0].page_start == 3 and out[0].page_end == 4
    assert store.last_top_k == 4


def test_score_floor_filters():
    store = _FakeStore([_stored("a", 0.1), _stored("b", 0.6)])
    r = Retriever(store, _FakeEmbedder(), top_k=4, score_floor=0.5)
    assert [c.chunk_id for c in r.retrieve("q")] == ["b"]

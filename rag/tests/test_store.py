from __future__ import annotations

from rag.store import ChunkStore, StoredChunk


def _store(tmp_path):
    return ChunkStore(tmp_path / "idx", "test_docs")


def test_upsert_then_query_returns_nearest_first(tmp_path):
    store = _store(tmp_path)
    store.upsert(
        ids=["a", "b", "c"],
        embeddings=[[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]],
        documents=["doc a", "doc b", "doc c"],
        metadatas=[{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}],
    )
    results = store.query([1.0, 0.0], top_k=2)
    assert [r.chunk_id for r in results] == ["a", "c"]
    assert isinstance(results[0], StoredChunk)
    assert results[0].score >= results[1].score
    assert 0.0 <= results[0].score <= 1.0
    assert results[0].metadata["doc_id"] == "a"


def test_count_and_reset(tmp_path):
    store = _store(tmp_path)
    store.upsert(ids=["a"], embeddings=[[1.0, 0.0]], documents=["x"], metadatas=[{}])
    assert store.count() == 1
    store.reset()
    assert store.count() == 0


def test_upsert_is_idempotent_on_id(tmp_path):
    store = _store(tmp_path)
    for text in ("first", "second"):
        store.upsert(ids=["a"], embeddings=[[1.0, 0.0]], documents=[text], metadatas=[{}])
    assert store.count() == 1
    assert store.query([1.0, 0.0], top_k=1)[0].text == "second"


def test_persists_across_instances(tmp_path):
    _store(tmp_path).upsert(ids=["a"], embeddings=[[1.0, 0.0]], documents=["x"], metadatas=[{}])
    assert ChunkStore(tmp_path / "idx", "test_docs").count() == 1

from __future__ import annotations

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int
    text: str
    score: float


class Retriever:
    def __init__(self, store, embedder, *, top_k: int, score_floor: float) -> None:
        self._store = store
        self._embedder = embedder
        self._top_k = top_k
        self._score_floor = score_floor

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        text = (query or "").strip()
        if not text:
            return []
        embedding = self._embedder.embed_one(text)
        stored = self._store.query(embedding, self._top_k)
        results: list[RetrievedChunk] = []
        for item in stored:
            if item.score < self._score_floor:
                continue
            meta = item.metadata
            results.append(
                RetrievedChunk(
                    chunk_id=item.chunk_id,
                    doc_id=meta.get("doc_id", ""),
                    doc_title=meta.get("doc_title", meta.get("doc_id", "")),
                    page_start=int(meta.get("page_start", 0)),
                    page_end=int(meta.get("page_end", 0)),
                    text=item.text,
                    score=item.score,
                )
            )
        results.sort(key=lambda c: c.score, reverse=True)
        return results

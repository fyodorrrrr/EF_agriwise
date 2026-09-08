from __future__ import annotations

from pydantic import BaseModel

from rag.config import RagConfig
from rag.generator import RagGenerationError
from rag.prompt import ChatTurn, build_messages
from rag.retriever import RetrievedChunk


class Citation(BaseModel):
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int


class RagAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    used_chunk_ids: list[str]


def _citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    seen: set[tuple[str, int, int]] = set()
    out: list[Citation] = []
    for chunk in chunks:
        key = (chunk.doc_id, chunk.page_start, chunk.page_end)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            Citation(
                doc_id=chunk.doc_id,
                doc_title=chunk.doc_title,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
        )
    return out


class RagPipeline:
    def __init__(self, retriever, generator) -> None:
        self._retriever = retriever
        self._generator = generator

    @classmethod
    def from_config(cls, cfg: RagConfig) -> RagPipeline:
        from rag.embeddings import Embedder
        from rag.generator import Generator
        from rag.retriever import Retriever
        from rag.store import ChunkStore

        embedder = Embedder(cfg.embedding_model)
        store = ChunkStore(cfg.index_dir, cfg.collection_name)
        retriever = Retriever(store, embedder, top_k=cfg.top_k, score_floor=cfg.score_floor)
        generator = Generator(cfg.groq_api_key, cfg.groq_model) if cfg.groq_api_key else None
        return cls(retriever, generator)

    @property
    def can_generate(self) -> bool:
        return self._generator is not None

    def answer(self, question: str, history: list[ChatTurn] | None = None) -> RagAnswer:
        if self._generator is None:
            raise RagGenerationError("generation unavailable: GROQ_API_KEY not configured")
        retrieved = self._retriever.retrieve(question)
        messages = build_messages(question, history or [], retrieved)
        text = self._generator.generate(messages)
        return RagAnswer(
            answer=text,
            citations=_citations(retrieved),
            used_chunk_ids=[chunk.chunk_id for chunk in retrieved],
        )

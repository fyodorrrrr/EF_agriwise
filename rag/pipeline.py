from __future__ import annotations

from pydantic import BaseModel

from rag.config import RagConfig
from rag.generator import RagGenerationError
from rag.prompt import ChatTurn, build_messages
from rag.retriever import RetrievedChunk


OUT_OF_SCOPE_ANSWER = (
    "I can only answer questions about the DA farm-business and good-agricultural-practice "
    "manuals for CALABARZON, plus the AgriWise analytics. Try asking about farm records, "
    "GAP requirements, crop planning, or commodity prices."
)

_SMALLTALK = {
    "hi", "hello", "hey", "yo", "hiya", "howdy", "hello there",
    "kumusta", "kamusta", "kumusta ka", "kamusta ka", "kamusta po", "kumusta po",
    "good morning", "good afternoon", "good evening",
    "magandang umaga", "magandang hapon", "magandang gabi",
    "thanks", "thank you", "thanks!", "salamat", "maraming salamat", "salamat po",
    "help", "what can you do", "what do you do", "who are you", "what are you",
    "what is this", "ano ito", "ano ka", "anong kaya mo",
}
_SMALLTALK_PREFIXES = ("hi", "hello", "hey", "kumusta", "kamusta", "salamat", "thanks")


def _is_smalltalk(question: str) -> bool:
    """Greetings / thanks / 'what can you do' — these retrieve nothing but should still
    get a warm reply from the model rather than the out-of-scope canned line."""
    q = question.strip().lower().rstrip("?!. ")
    if q in _SMALLTALK:
        return True
    first = q.split(" ", 1)[0]
    return len(q) <= 16 and first in _SMALLTALK_PREFIXES


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

    def warmup(self) -> None:
        """Force the embedding model to load now, so the first request doesn't pay for it
        and a model-download failure surfaces at startup (as a 503) not mid-request (as a 500)."""
        self._retriever.retrieve("warmup")

    def answer(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
        analytics_context: str | None = None,
    ) -> RagAnswer:
        if self._generator is None:
            raise RagGenerationError("generation unavailable: GROQ_API_KEY not configured")

        smalltalk = _is_smalltalk(question)
        retrieved = [] if smalltalk else self._retriever.retrieve(question)

        # Nothing relevant and not a greeting → out of scope. Answer deterministically
        # without spending a generation call (also blocks code/homework/injection asks).
        # Analytics context is its own grounding, so keep going when it is present.
        if not smalltalk and not retrieved and not analytics_context:
            return RagAnswer(answer=OUT_OF_SCOPE_ANSWER, citations=[], used_chunk_ids=[])

        messages = build_messages(
            question, history or [], retrieved, analytics_context=analytics_context
        )
        text = self._generator.generate(messages)
        return RagAnswer(
            answer=text,
            citations=_citations(retrieved),
            used_chunk_ids=[chunk.chunk_id for chunk in retrieved],
        )

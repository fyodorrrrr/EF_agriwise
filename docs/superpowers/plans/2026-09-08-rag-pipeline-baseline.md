# RAG Pipeline Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a document-only "Ask AgriWise" RAG chatbot — offline PDF ingestion, local embeddings, a Chroma vector store, Groq generation, a `POST /rag/query` endpoint, and a multi-turn chat page.

**Architecture:** All Python lives in one uv project rooted at the repo root, exposing two flat packages: `rag` (ingestion + retrieval + generation) and `app` (FastAPI). Ingestion is an offline CLI that extracts text with pypdf, cleans it, splits it into ~500-character chunks, embeds them with a local sentence-transformers model, and persists them to a Chroma collection under `data/processed/`. At API startup a single `RagPipeline` is built and cached on `app.state`; `POST /rag/query` retrieves the top-4 chunks, builds a grounded prompt with recent conversation history, calls Groq, and returns the answer plus citations derived from the retrieved chunks. The Next.js chat page renders a multi-turn conversation and each answer's citations.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic, pypdf, sentence-transformers (`all-MiniLM-L6-v2`), chromadb, groq, pytest, reportlab (test fixtures) · Next.js 16 App Router, React 19, TypeScript, Tailwind 4, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-08-rag-pipeline-baseline-design.md` — read it alongside this plan.

## Global Constraints

- Do not modify anything in `data/raw/` in place. Derived data (the Chroma index) belongs in `data/processed/` and is gitignored.
- Ingestion and retrieval must run fully offline. Only answer generation calls an external service (Groq).
- Supported source documents are exactly the three PDFs in `data/raw/`: `BAFS_explanatory_manual.pdf`, `Farm_business_school_manual.pdf`, `PAFES_manual_of_operations.pdf`.
- Configuration values, exact defaults: `GROQ_MODEL=openai/gpt-oss-120b`, `EMBEDDING_MODEL=all-MiniLM-L6-v2`, `RAG_CHUNK_SIZE=500` (characters), `RAG_CHUNK_OVERLAP=50` (characters), `RAG_TOP_K=4`, `RAG_INDEX_DIR=data/processed/rag_index`, `RAG_SCORE_FLOOR=0.0`.
- Chunk size and overlap are measured in **characters**, never tokens.
- No authentication, no rate limiting, no server-side persistence of conversations.
- When `GROQ_API_KEY` is unset or Groq fails, `POST /rag/query` returns HTTP 503 with a clear `detail` message; retrieval-only code paths must still work and stay tested.
- Citations are derived from the retrieved chunk set (deduped by `doc_id` + page range), never parsed out of the model's text.
- Structured analytics-context injection is **out of scope** (Sprint 5). `build_messages` keeps an unused `analytics_context` parameter as the only forward accommodation.
- No test may call Groq or download the embedding model. Use injected fakes / monkeypatched clients. The one real end-to-end ingestion test is marked slow and runs on a reportlab-generated fixture PDF.
- Python: 4-space indent, `from __future__ import annotations` at the top of every `rag` module, type hints on all public functions, ruff clean (`line-length = 100`, `target-version = "py312"`).

---

## File Structure

**Created — `rag/` package:**
- `rag/__init__.py` — empty package marker
- `rag/config.py` — `RagConfig` frozen dataclass + `RagConfig.from_env()`
- `rag/chunking.py` — `PageText`, `Chunk` dataclasses + `chunk_pages()`
- `rag/embeddings.py` — `Embedder` (lazy sentence-transformers wrapper)
- `rag/store.py` — `StoredChunk` + `ChunkStore` (Chroma wrapper)
- `rag/retriever.py` — `RetrievedChunk` model + `Retriever`
- `rag/prompt.py` — `ChatTurn` model, `SYSTEM_PROMPT`, `build_messages()`
- `rag/generator.py` — `RagGenerationError` + `Generator` (Groq wrapper)
- `rag/pipeline.py` — `Citation`, `RagAnswer` models + `RagPipeline`
- `rag/ingest.py` — cleaning helpers, `extract_pages()`, `prepare_pages()`, `ingest()`, `main()` CLI

**Created — `rag/tests/`:**
- `rag/tests/__init__.py`, `rag/tests/conftest.py` (fixture-PDF factory)
- `test_config.py`, `test_chunking.py`, `test_embeddings.py`, `test_store.py`, `test_retriever.py`, `test_prompt.py`, `test_generator.py`, `test_pipeline.py`, `test_ingest.py`

**Created — API:**
- `apps/api/app/schemas/rag.py` — `ChatMessage`, `RagQueryRequest`, `Citation`, `RagQueryResponse`
- `apps/api/app/routers/rag.py` — `router` + `get_pipeline` dependency
- `apps/api/tests/test_rag_router.py`

**Modified — API:**
- `apps/api/app/config.py` — add RAG settings + `build_rag_config()`
- `apps/api/app/main.py` — lifespan builds/caches `RagPipeline`, include `rag` router
- `apps/api/.env.example` — add RAG keys

**Created — Web:**
- `apps/web/src/types/rag.ts` — request/response types
- `apps/web/src/lib/rag.ts` — `askAgriWise()` client + `apps/web/src/lib/rag.test.ts`
- `apps/web/src/app/chat/page.tsx` — chat UI + `apps/web/src/app/chat/page.test.tsx`

**Modified — Web:**
- `apps/web/src/app/page.tsx` — add a link to `/chat`

**Created / Modified — repo root:**
- `pyproject.toml` — new single-root uv project (replaces `apps/api/pyproject.toml`)
- `.python-version` — moved from `apps/api/`
- `README.md` — RAG section
- `apps/api/README.md` — run/ingest instructions
- Deleted: `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/.python-version`

---

## Task 1: Consolidate Python into one uv project + `rag` config

**Files:**
- Create: `pyproject.toml` (repo root)
- Create: `.python-version` (repo root)
- Delete: `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/.python-version`
- Create: `rag/__init__.py`, `rag/config.py`
- Create: `rag/tests/__init__.py`, `rag/tests/test_config.py`
- Modify: `.gitignore` (add `.venv/`, `data/processed/rag_index/` already covered by `data/processed/*`)

**Interfaces:**
- Produces:
  - `rag.config.RagConfig` — frozen dataclass with fields `groq_api_key: str | None = None`, `groq_model: str = "openai/gpt-oss-120b"`, `embedding_model: str = "all-MiniLM-L6-v2"`, `chunk_size: int = 500`, `chunk_overlap: int = 50`, `top_k: int = 4`, `index_dir: pathlib.Path = Path("data/processed/rag_index")`, `score_floor: float = 0.0`, `collection_name: str = "agriwise_docs"`
  - `RagConfig.from_env(environ: Mapping[str, str] | None = None) -> RagConfig` — reads `GROQ_API_KEY`, `GROQ_MODEL`, `EMBEDDING_MODEL`, `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_TOP_K`, `RAG_INDEX_DIR`, `RAG_SCORE_FLOOR`

- [ ] **Step 1: Remove the nested api uv project**

```bash
git rm apps/api/pyproject.toml apps/api/uv.lock apps/api/.python-version
rm -rf apps/api/.venv
```

- [ ] **Step 2: Write the repo-root `pyproject.toml`**

```toml
[project]
name = "agriwise"
version = "0.1.0"
description = "AgriWise — CALABARZON agriculture analytics API and RAG pipeline"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.141.1",
    "uvicorn[standard]>=0.52.4",
    "pydantic>=2.13.5",
    "pydantic-settings>=2.15.0",
    "pypdf>=6.0",
    "sentence-transformers>=5.0",
    "chromadb>=1.5",
    "groq>=1.6",
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
    "httpx>=0.28.1",
    "ruff>=0.16.6",
    "reportlab>=4.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["rag", "apps/api/app"]

[tool.pytest.ini_options]
testpaths = ["apps/api/tests", "rag/tests"]
markers = ["slow: end-to-end tests that build a real index"]

[tool.ruff]
target-version = "py312"
line-length = 100
extend-exclude = [".venv", "apps/web"]
```

- [ ] **Step 3: Create `.python-version` at repo root**

```
3.12
```

- [ ] **Step 4: Create the `rag` package files**

`rag/__init__.py`: empty file.

`rag/config.py`:

```python
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_INDEX_DIR = Path("data/processed/rag_index")


@dataclass(frozen=True)
class RagConfig:
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4
    index_dir: Path = field(default=DEFAULT_INDEX_DIR)
    score_floor: float = 0.0
    collection_name: str = "agriwise_docs"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> RagConfig:
        env = os.environ if environ is None else environ
        defaults = cls()
        return cls(
            groq_api_key=env.get("GROQ_API_KEY") or None,
            groq_model=env.get("GROQ_MODEL", defaults.groq_model),
            embedding_model=env.get("EMBEDDING_MODEL", defaults.embedding_model),
            chunk_size=int(env.get("RAG_CHUNK_SIZE", defaults.chunk_size)),
            chunk_overlap=int(env.get("RAG_CHUNK_OVERLAP", defaults.chunk_overlap)),
            top_k=int(env.get("RAG_TOP_K", defaults.top_k)),
            index_dir=Path(env.get("RAG_INDEX_DIR", str(defaults.index_dir))),
            score_floor=float(env.get("RAG_SCORE_FLOOR", defaults.score_floor)),
        )
```

- [ ] **Step 5: Write the failing test**

`rag/tests/__init__.py`: empty file. `rag/tests/test_config.py`:

```python
from __future__ import annotations

from pathlib import Path

from rag.config import RagConfig


def test_defaults_match_spec():
    cfg = RagConfig()
    assert cfg.groq_model == "openai/gpt-oss-120b"
    assert cfg.embedding_model == "all-MiniLM-L6-v2"
    assert cfg.chunk_size == 500
    assert cfg.chunk_overlap == 50
    assert cfg.top_k == 4
    assert cfg.index_dir == Path("data/processed/rag_index")
    assert cfg.score_floor == 0.0
    assert cfg.collection_name == "agriwise_docs"
    assert cfg.groq_api_key is None


def test_from_env_overrides_and_types():
    cfg = RagConfig.from_env(
        {
            "GROQ_API_KEY": "sk-test",
            "RAG_CHUNK_SIZE": "800",
            "RAG_TOP_K": "6",
            "RAG_SCORE_FLOOR": "0.25",
            "RAG_INDEX_DIR": "/tmp/idx",
        }
    )
    assert cfg.groq_api_key == "sk-test"
    assert cfg.chunk_size == 800
    assert cfg.top_k == 6
    assert cfg.score_floor == 0.25
    assert cfg.index_dir == Path("/tmp/idx")
    # untouched keys keep defaults
    assert cfg.groq_model == "openai/gpt-oss-120b"


def test_from_env_blank_api_key_is_none():
    assert RagConfig.from_env({"GROQ_API_KEY": ""}).groq_api_key is None
```

- [ ] **Step 6: Sync the environment and run the test to verify it fails then passes**

```bash
uv sync
uv run pytest rag/tests/test_config.py -v
```
Expected: `uv sync` installs the consolidated deps (first run downloads torch — allow several minutes). Tests PASS. If they were written before `rag/config.py`, they fail with `ModuleNotFoundError: rag`.

- [ ] **Step 7: Verify the existing health test still passes under the new layout**

```bash
uv run pytest apps/api/tests/test_health.py -v
```
Expected: PASS (imports `app.main`, now resolved via the editable root install).

- [ ] **Step 8: Lint**

```bash
uv run ruff check rag apps/api
```
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .python-version rag/ .gitignore
git add -u apps/api
git commit -m "chore: consolidate python into one uv project; add rag.config"
```

---

## Task 2: Text chunking

**Files:**
- Create: `rag/chunking.py`
- Create: `rag/tests/test_chunking.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `rag.chunking.PageText` — frozen dataclass `{doc_id: str, doc_title: str, page_number: int, text: str}`
  - `rag.chunking.Chunk` — frozen dataclass `{chunk_id: str, doc_id: str, doc_title: str, page_start: int, page_end: int, text: str}`
  - `rag.chunking.chunk_pages(pages: list[PageText], *, chunk_size: int, chunk_overlap: int) -> list[Chunk]` — concatenates one document's pages (joined by `"\n\n"`), splits into ≤`chunk_size`-char windows preferring paragraph/sentence/space breaks past the halfway point, applies `chunk_overlap`, tracks the page span each chunk covers. `chunk_id` is `"<doc_id>::<index>"` starting at 0. Returns `[]` for empty input. Assumes all pages share one `doc_id`/`doc_title` (the first page's).

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from rag.chunking import Chunk, PageText, chunk_pages


def _pages(*texts: str, doc_id: str = "doc", title: str = "Doc") -> list[PageText]:
    return [
        PageText(doc_id=doc_id, doc_title=title, page_number=i, text=t)
        for i, t in enumerate(texts, start=1)
    ]


def test_empty_input_returns_empty():
    assert chunk_pages([], chunk_size=500, chunk_overlap=50) == []


def test_short_single_page_is_one_chunk():
    chunks = chunk_pages(_pages("Record every farm expense in the ledger."),
                         chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert isinstance(chunks[0], Chunk)
    assert chunks[0].chunk_id == "doc::0"
    assert chunks[0].page_start == 1 and chunks[0].page_end == 1
    assert "farm expense" in chunks[0].text


def test_long_text_splits_with_size_and_overlap():
    body = ". ".join(f"sentence number {n} about good agricultural practice" for n in range(60))
    chunks = chunk_pages(_pages(body), chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 3
    for c in chunks:
        assert len(c.text) <= 240  # size + tolerance for the break search window
    # consecutive chunks overlap somewhere
    assert chunks[0].text[-20:] in (chunks[1].text[:120] + chunks[1].text)
    # ids are sequential
    assert [c.chunk_id for c in chunks] == [f"doc::{i}" for i in range(len(chunks))]


def test_page_span_tracks_source_pages():
    p1 = "alpha " * 60          # ~360 chars
    p2 = "bravo " * 60
    chunks = chunk_pages(_pages(p1, p2), chunk_size=200, chunk_overlap=20)
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2
    assert any(c.page_start == 1 and c.page_end == 2 for c in chunks) or (
        chunks[0].page_end == 1 and chunks[-1].page_start == 2
    )


def test_blank_pages_are_skipped_in_concatenation():
    chunks = chunk_pages(_pages("real content here about GAP", "   ", "more real content"),
                         chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert "GAP" in chunks[0].text and "more real content" in chunks[0].text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest rag/tests/test_chunking.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError: cannot import name 'chunk_pages'`.

- [ ] **Step 3: Write minimal implementation**

`rag/chunking.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

_BREAKS = ("\n\n", "\n", ". ", " ")


@dataclass(frozen=True)
class PageText:
    doc_id: str
    doc_title: str
    page_number: int
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int
    text: str


def _best_break(window: str) -> int:
    half = len(window) // 2
    for sep in _BREAKS:
        pos = window.rfind(sep)
        if pos > half:
            return pos + len(sep)
    return len(window)


def chunk_pages(pages: list[PageText], *, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    if not pages:
        return []
    doc_id = pages[0].doc_id
    doc_title = pages[0].doc_title

    parts: list[str] = []
    page_at: list[int] = []
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        if parts:
            parts.append("\n\n")
            page_at.extend([page.page_number, page.page_number])
        parts.append(text)
        page_at.extend([page.page_number] * len(text))
    full = "".join(parts)
    if not full:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    length = len(full)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            end = start + _best_break(full[start:end])
        piece = full[start:end].strip()
        if piece:
            lo = page_at[min(start, len(page_at) - 1)]
            hi = page_at[min(end - 1, len(page_at) - 1)]
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}::{index}",
                    doc_id=doc_id,
                    doc_title=doc_title,
                    page_start=min(lo, hi),
                    page_end=max(lo, hi),
                    text=piece,
                )
            )
            index += 1
        if end >= length:
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest rag/tests/test_chunking.py -v`
Expected: PASS (all 5).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check rag/chunking.py rag/tests/test_chunking.py
git add rag/chunking.py rag/tests/test_chunking.py
git commit -m "feat: add character-based page chunker"
```

---

## Task 3: Embedding model wrapper

**Files:**
- Create: `rag/embeddings.py`
- Create: `rag/tests/test_embeddings.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `rag.embeddings.Embedder` — `Embedder(model_name: str)`; `embed(texts: list[str]) -> list[list[float]]` (returns `[]` for `[]`, otherwise L2-normalized vectors as plain lists); `embed_one(text: str) -> list[float]`. The underlying `sentence_transformers.SentenceTransformer` is imported and constructed lazily on first use and cached.

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import sys
import types

import pytest

from rag.embeddings import Embedder


class _FakeST:
    instances: list[str] = []

    def __init__(self, model_name: str):
        self.model_name = model_name
        _FakeST.instances.append(model_name)

    def encode(self, texts, normalize_embeddings=False, batch_size=32):
        import numpy as np

        return np.array([[float(len(t)), 1.0, 0.0] for t in texts])


@pytest.fixture(autouse=True)
def _fake_sentence_transformers(monkeypatch):
    _FakeST.instances = []
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = _FakeST
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    yield


def test_embed_empty_returns_empty_without_loading_model():
    embedder = Embedder("all-MiniLM-L6-v2")
    assert embedder.embed([]) == []
    assert _FakeST.instances == []


def test_embed_returns_plain_lists():
    embedder = Embedder("all-MiniLM-L6-v2")
    out = embedder.embed(["ab", "abcd"])
    assert out == [[2.0, 1.0, 0.0], [4.0, 1.0, 0.0]]
    assert isinstance(out[0], list)


def test_model_constructed_once_and_cached():
    embedder = Embedder("all-MiniLM-L6-v2")
    embedder.embed(["x"])
    embedder.embed_one("y")
    assert _FakeST.instances == ["all-MiniLM-L6-v2"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest rag/tests/test_embeddings.py -v`
Expected: FAIL with `ImportError: cannot import name 'Embedder'`.

- [ ] **Step 3: Write minimal implementation**

`rag/embeddings.py`:

```python
from __future__ import annotations

from functools import cached_property


class Embedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def _model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [list(map(float, row)) for row in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest rag/tests/test_embeddings.py -v`
Expected: PASS (3).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check rag/embeddings.py rag/tests/test_embeddings.py
git add rag/embeddings.py rag/tests/test_embeddings.py
git commit -m "feat: add lazy sentence-transformers embedder"
```

---

## Task 4: Chroma chunk store

**Files:**
- Create: `rag/store.py`
- Create: `rag/tests/test_store.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `rag.store.StoredChunk` — frozen dataclass `{chunk_id: str, text: str, metadata: dict, score: float}` (`score` is cosine similarity in `[0, 1]`, computed as `max(0.0, 1.0 - distance)`)
  - `rag.store.ChunkStore` — `ChunkStore(index_dir: pathlib.Path, collection_name: str)` opens/creates a persistent Chroma collection with cosine space. Methods:
    - `upsert(*, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None`
    - `query(embedding: list[float], top_k: int) -> list[StoredChunk]` (nearest first)
    - `reset() -> None` (drop and recreate the collection)
    - `count() -> int`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest rag/tests/test_store.py -v`
Expected: FAIL with `ImportError: cannot import name 'ChunkStore'`.

- [ ] **Step 3: Write minimal implementation**

`rag/store.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: str
    text: str
    metadata: dict
    score: float


class ChunkStore:
    def __init__(self, index_dir: Path, collection_name: str) -> None:
        import chromadb

        self._name = collection_name
        self._client = chromadb.PersistentClient(path=str(index_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        self._collection.upsert(
            ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )

    def query(self, embedding: list[float], top_k: int) -> list[StoredChunk]:
        res = self._collection.query(query_embeddings=[embedding], n_results=top_k)
        ids = res["ids"][0]
        documents = res["documents"][0]
        metadatas = res["metadatas"][0]
        distances = res["distances"][0]
        out: list[StoredChunk] = []
        for chunk_id, text, meta, distance in zip(ids, documents, metadatas, distances):
            out.append(
                StoredChunk(
                    chunk_id=chunk_id,
                    text=text,
                    metadata=dict(meta or {}),
                    score=max(0.0, 1.0 - float(distance)),
                )
            )
        return out

    def reset(self) -> None:
        self._client.delete_collection(self._name)
        self._collection = self._client.get_or_create_collection(
            name=self._name, metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        return self._collection.count()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest rag/tests/test_store.py -v`
Expected: PASS (4). Chroma writes to `tmp_path`; no network.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check rag/store.py rag/tests/test_store.py
git add rag/store.py rag/tests/test_store.py
git commit -m "feat: add chroma-backed chunk store"
```

---

## Task 5: Retriever

**Files:**
- Create: `rag/retriever.py`
- Create: `rag/tests/test_retriever.py`

**Interfaces:**
- Consumes:
  - `rag.store.StoredChunk`, `rag.store.ChunkStore` (duck-typed: any object with `query(embedding, top_k) -> list[StoredChunk]`)
  - `rag.embeddings.Embedder` (duck-typed: any object with `embed_one(text) -> list[float]`)
- Produces:
  - `rag.retriever.RetrievedChunk` — Pydantic `BaseModel` `{chunk_id: str, doc_id: str, doc_title: str, page_start: int, page_end: int, text: str, score: float}`
  - `rag.retriever.Retriever` — `Retriever(store, embedder, *, top_k: int, score_floor: float)`; `retrieve(query: str) -> list[RetrievedChunk]` returns `[]` for blank query, embeds the query, calls `store.query`, drops chunks with `score < score_floor`, and returns them sorted by `score` descending. Reads `doc_id`, `doc_title`, `page_start`, `page_end` from each `StoredChunk.metadata`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest rag/tests/test_retriever.py -v`
Expected: FAIL with `ImportError: cannot import name 'Retriever'`.

- [ ] **Step 3: Write minimal implementation**

`rag/retriever.py`:

```python
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
                    doc_id=meta["doc_id"],
                    doc_title=meta["doc_title"],
                    page_start=int(meta["page_start"]),
                    page_end=int(meta["page_end"]),
                    text=item.text,
                    score=item.score,
                )
            )
        results.sort(key=lambda c: c.score, reverse=True)
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest rag/tests/test_retriever.py -v`
Expected: PASS (3).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check rag/retriever.py rag/tests/test_retriever.py
git add rag/retriever.py rag/tests/test_retriever.py
git commit -m "feat: add retriever over embedder + chunk store"
```

---

## Task 6: Prompt builder

**Files:**
- Create: `rag/prompt.py`
- Create: `rag/tests/test_prompt.py`

**Interfaces:**
- Consumes: `rag.retriever.RetrievedChunk`
- Produces:
  - `rag.prompt.ChatTurn` — Pydantic `BaseModel` `{role: Literal["user", "assistant"], content: str}`
  - `rag.prompt.SYSTEM_PROMPT: str`
  - `rag.prompt.MAX_HISTORY_TURNS: int = 6`
  - `rag.prompt.build_messages(question: str, history: list[ChatTurn], retrieved: list[RetrievedChunk], analytics_context: str | None = None) -> list[dict]` — returns Groq-style `{"role", "content"}` messages: system prompt; then, only if `analytics_context` is truthy, a **separate** system message prefixed `Current AgriWise analytics context:`; then the last `MAX_HISTORY_TURNS` history turns verbatim; then a user message containing the citation-tagged excerpt block and the question. Each excerpt is tagged `[<doc_title>, p.<start>]` or `[<doc_title>, p.<start>-<end>]`. When `retrieved` is empty the excerpt block reads `No manual excerpts were retrieved for this question.`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from rag.prompt import MAX_HISTORY_TURNS, SYSTEM_PROMPT, build_messages
from rag.prompt import ChatTurn
from rag.retriever import RetrievedChunk


def _chunk(title: str, ps: int, pe: int, text: str = "excerpt body") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{title}::0", doc_id=title, doc_title=title,
        page_start=ps, page_end=pe, text=text, score=0.5,
    )


def test_system_prompt_first_and_rules_present():
    msgs = build_messages("q", [], [_chunk("Doc", 1, 1)])
    assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}
    lowered = SYSTEM_PROMPT.lower()
    assert "cite" in lowered
    assert "do not" in lowered  # refusal / no-outside-knowledge language


def test_citation_tags_use_page_ranges():
    msgs = build_messages("q", [], [_chunk("GAP Manual", 5, 5), _chunk("FBS Manual", 8, 9)])
    user = msgs[-1]["content"]
    assert "[GAP Manual, p.5]" in user
    assert "[FBS Manual, p.8-9]" in user
    assert user.rstrip().endswith("q")


def test_history_is_trimmed_to_max_turns():
    history = [ChatTurn(role="user", content=f"m{i}") for i in range(10)]
    msgs = build_messages("now", history, [_chunk("Doc", 1, 1)])
    history_msgs = [m for m in msgs if m["content"].startswith("m")]
    assert [m["content"] for m in history_msgs] == [f"m{i}" for i in range(4, 10)]
    assert len(history_msgs) == MAX_HISTORY_TURNS


def test_empty_retrieval_has_explicit_note():
    user = build_messages("q", [], [])[-1]["content"]
    assert "No manual excerpts were retrieved" in user


def test_analytics_context_is_separate_and_optional():
    without = build_messages("q", [], [_chunk("Doc", 1, 1)])
    assert all("analytics context" not in m["content"].lower() for m in without)

    with_ctx = build_messages("q", [], [_chunk("Doc", 1, 1)], analytics_context="Rice demand: USABLE_PROXY")
    ctx_msgs = [m for m in with_ctx if "analytics context" in m["content"].lower()]
    assert len(ctx_msgs) == 1
    assert ctx_msgs[0]["role"] == "system"
    assert "Rice demand: USABLE_PROXY" in ctx_msgs[0]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest rag/tests/test_prompt.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

`rag/prompt.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from rag.retriever import RetrievedChunk

MAX_HISTORY_TURNS = 6

SYSTEM_PROMPT = """You are AgriWise, an assistant for smallholder farmers and agricultural \
extension workers in the CALABARZON region of the Philippines.

Rules:
- Answer only from the numbered manual excerpts provided in the user message. Do not use \
outside knowledge.
- Cite every claim with the bracketed tag of the excerpt it came from, for example \
[Farm Business School Manual, p.88].
- If the excerpts do not contain the answer, say so plainly and suggest contacting a local \
agricultural technician or the Department of Agriculture. Do not guess.
- Do not give medical, legal, or pesticide-dosage advice; refer the farmer to a local \
agricultural technician or the Department of Agriculture.
- Be concise, practical, and neutral."""


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


def _page_tag(chunk: RetrievedChunk) -> str:
    if chunk.page_start == chunk.page_end:
        pages = f"p.{chunk.page_start}"
    else:
        pages = f"p.{chunk.page_start}-{chunk.page_end}"
    return f"[{chunk.doc_title}, {pages}]"


def _excerpt_block(retrieved: list[RetrievedChunk]) -> str:
    if not retrieved:
        return "No manual excerpts were retrieved for this question."
    return "\n\n".join(f"{_page_tag(chunk)}\n{chunk.text}" for chunk in retrieved)


def build_messages(
    question: str,
    history: list[ChatTurn],
    retrieved: list[RetrievedChunk],
    analytics_context: str | None = None,
) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if analytics_context:
        messages.append(
            {
                "role": "system",
                "content": f"Current AgriWise analytics context:\n{analytics_context}",
            }
        )
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(
        {
            "role": "user",
            "content": f"Manual excerpts:\n\n{_excerpt_block(retrieved)}\n\nQuestion: {question}",
        }
    )
    return messages
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest rag/tests/test_prompt.py -v`
Expected: PASS (5).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check rag/prompt.py rag/tests/test_prompt.py
git add rag/prompt.py rag/tests/test_prompt.py
git commit -m "feat: add grounded prompt builder with citation tags"
```

---

## Task 7: Groq generator

**Files:**
- Create: `rag/generator.py`
- Create: `rag/tests/test_generator.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `rag.generator.RagGenerationError` — subclass of `RuntimeError`
  - `rag.generator.Generator` — `Generator(api_key: str, model: str, *, timeout_s: float = 30.0)` constructs a `groq.Groq` client lazily; `generate(messages: list[dict]) -> str` calls `client.chat.completions.create(model=..., messages=..., temperature=0.2)` and returns `choices[0].message.content or ""`. Any exception from the client is re-raised as `RagGenerationError`.

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import sys
import types

import pytest

from rag.generator import Generator, RagGenerationError


class _Msg:
    def __init__(self, content):
        self.message = types.SimpleNamespace(content=content)


class _FakeCompletions:
    def __init__(self, *, content="hello", boom=False):
        self.content = content
        self.boom = boom
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.boom:
            raise RuntimeError("groq is down")
        return types.SimpleNamespace(choices=[_Msg(self.content)])


class _FakeGroq:
    last: "_FakeGroq | None" = None

    def __init__(self, api_key=None, timeout=None):
        self.api_key = api_key
        self.timeout = timeout
        self.completions = _FakeCompletions()
        self.chat = types.SimpleNamespace(completions=self.completions)
        _FakeGroq.last = self


@pytest.fixture(autouse=True)
def _fake_groq(monkeypatch):
    module = types.ModuleType("groq")
    module.Groq = _FakeGroq
    monkeypatch.setitem(sys.modules, "groq", module)
    yield


def test_generate_passes_model_and_temperature():
    gen = Generator("sk-test", "openai/gpt-oss-120b")
    out = gen.generate([{"role": "user", "content": "hi"}])
    assert out == "hello"
    call = _FakeGroq.last.completions.calls[0]
    assert call["model"] == "openai/gpt-oss-120b"
    assert call["temperature"] == 0.2
    assert _FakeGroq.last.api_key == "sk-test"


def test_none_content_becomes_empty_string():
    gen = Generator("sk-test", "m")
    _FakeGroq.last = None
    gen.generate([{"role": "user", "content": "hi"}])
    _FakeGroq.last.completions.content = None
    assert gen.generate([{"role": "user", "content": "hi"}]) == ""


def test_client_errors_are_wrapped():
    gen = Generator("sk-test", "m")
    _FakeGroq.last.completions.boom = True
    with pytest.raises(RagGenerationError):
        gen.generate([{"role": "user", "content": "hi"}])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest rag/tests/test_generator.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

`rag/generator.py`:

```python
from __future__ import annotations

from functools import cached_property


class RagGenerationError(RuntimeError):
    pass


class Generator:
    def __init__(self, api_key: str, model: str, *, timeout_s: float = 30.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s

    @cached_property
    def _client(self):
        from groq import Groq

        return Groq(api_key=self._api_key, timeout=self._timeout_s)

    def generate(self, messages: list[dict]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model, messages=messages, temperature=0.2
            )
        except Exception as exc:  # noqa: BLE001 - deliberately wrap any client failure
            raise RagGenerationError(str(exc)) from exc
        return response.choices[0].message.content or ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest rag/tests/test_generator.py -v`
Expected: PASS (3).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check rag/generator.py rag/tests/test_generator.py
git add rag/generator.py rag/tests/test_generator.py
git commit -m "feat: add groq generator wrapper"
```

---

## Task 8: RAG pipeline

**Files:**
- Create: `rag/pipeline.py`
- Create: `rag/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `rag.config.RagConfig`, `rag.prompt.ChatTurn`, `rag.prompt.build_messages`, `rag.retriever.RetrievedChunk`, `rag.retriever.Retriever`, `rag.generator.Generator`, `rag.embeddings.Embedder`, `rag.store.ChunkStore`
- Produces:
  - `rag.pipeline.Citation` — Pydantic `BaseModel` `{doc_id: str, doc_title: str, page_start: int, page_end: int}`
  - `rag.pipeline.RagAnswer` — Pydantic `BaseModel` `{answer: str, citations: list[Citation], used_chunk_ids: list[str]}`
  - `rag.pipeline.RagPipeline` — `RagPipeline(retriever, generator_or_none)`:
    - `RagPipeline.from_config(cfg: RagConfig) -> RagPipeline` builds `Embedder`, `ChunkStore`, `Retriever`, and (only if `cfg.groq_api_key`) `Generator`.
    - `can_generate: bool` property — `True` when a generator is configured.
    - `answer(question: str, history: list[ChatTurn] | None = None) -> RagAnswer` — raises `RagGenerationError` (from `rag.generator`) if `can_generate` is `False`; otherwise retrieves, builds messages (no analytics context), calls the generator, and returns the answer with citations deduped by `(doc_id, page_start, page_end)` preserving retrieval order, and `used_chunk_ids` in retrieval order.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest rag/tests/test_pipeline.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

`rag/pipeline.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest rag/tests/test_pipeline.py -v`
Expected: PASS (3).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check rag/pipeline.py rag/tests/test_pipeline.py
git add rag/pipeline.py rag/tests/test_pipeline.py
git commit -m "feat: assemble rag pipeline (retrieve -> prompt -> generate)"
```

---

## Task 9: Ingestion CLI

**Files:**
- Create: `rag/ingest.py`
- Create: `rag/tests/conftest.py`
- Create: `rag/tests/test_ingest.py`

**Interfaces:**
- Consumes: `rag.chunking.PageText`, `rag.chunking.chunk_pages`, `rag.config.RagConfig`, `rag.embeddings.Embedder`, `rag.store.ChunkStore`
- Produces:
  - `rag.ingest.DOC_TITLES: dict[str, str]` — stem → human title for the three known PDFs
  - `rag.ingest.MIN_PAGE_CHARS: int = 100`
  - `rag.ingest.clean_page(text: str) -> str` — de-hyphenate `\w-\n\w`, collapse spaces/tabs, collapse 3+ newlines to 2, strip
  - `rag.ingest.detect_running_lines(pages: list[str], *, min_fraction: float = 0.5) -> set[str]` — short lines (≤80 chars) appearing on ≥ `max(3, len(pages) * min_fraction)` pages
  - `rag.ingest.strip_running_lines(text: str, running: set[str]) -> str`
  - `rag.ingest.extract_pages(pdf_path: pathlib.Path) -> list[PageText]` — one `PageText` per page via `pypdf`
  - `rag.ingest.prepare_pages(raw_pages: list[PageText]) -> list[PageText]` — clean, strip running lines, drop pages `< MIN_PAGE_CHARS`
  - `rag.ingest.ingest(cfg: RagConfig, *, sources: list[pathlib.Path] | None = None, rebuild: bool = False) -> dict` — full pipeline, writes `<index_dir>/manifest.json`, returns the manifest dict `{embedding_model, chunk_size, chunk_overlap, generated_at, documents: {stem: {chunks, sha256}}}`. Default `sources` = sorted `data/raw/*.pdf`.
  - `rag.ingest.main(argv: list[str] | None = None) -> None` — argparse CLI: `--source` (repeatable `Path`), `--rebuild` (flag). Builds `RagConfig.from_env()`, calls `ingest`, prints a one-line summary.
- Module is runnable as `python -m rag.ingest` (add `if __name__ == "__main__": main()`).

- [ ] **Step 1: Write the conftest fixture-PDF factory**

`rag/tests/conftest.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def make_pdf(tmp_path):
    def _make(name: str, pages: list[str]) -> Path:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas

        path = tmp_path / name
        pdf = canvas.Canvas(str(path), pagesize=LETTER)
        for body in pages:
            text = pdf.beginText(72, 720)
            for line in body.splitlines() or [""]:
                text.textLine(line)
            pdf.drawText(text)
            pdf.showPage()
        pdf.save()
        return path

    return _make
```

- [ ] **Step 2: Write the failing tests**

`rag/tests/test_ingest.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag.config import RagConfig
from rag.ingest import (
    clean_page,
    detect_running_lines,
    extract_pages,
    ingest,
    prepare_pages,
    strip_running_lines,
)


def test_clean_page_dehyphenates_and_collapses_whitespace():
    raw = "good agri-\nculture   practice\n\n\n\nnext line"
    cleaned = clean_page(raw)
    assert "agriculture practice" in cleaned
    assert "\n\n\n" not in cleaned
    assert "   " not in cleaned


def test_detect_and_strip_running_lines():
    pages = ["HEADER\nreal content one", "HEADER\nreal content two", "HEADER\nreal content three"]
    running = detect_running_lines(pages)
    assert "HEADER" in running
    assert strip_running_lines(pages[0], running).strip() == "real content one"


def test_prepare_pages_drops_short_pages():
    from rag.chunking import PageText

    raw = [
        PageText("d", "D", 1, "x " * 200),          # long -> kept
        PageText("d", "D", 2, "tiny"),               # short -> dropped
    ]
    prepared = prepare_pages(raw)
    assert [p.page_number for p in prepared] == [1]


def test_extract_pages_reads_text(make_pdf):
    pdf = make_pdf("BAFS_explanatory_manual.pdf", ["Code of GAP for fruits and vegetables", "page two body"])
    pages = extract_pages(pdf)
    assert len(pages) == 2
    assert pages[0].doc_id == "BAFS_explanatory_manual"
    assert pages[0].doc_title  # mapped title, non-empty
    assert "GAP" in pages[0].text


@pytest.mark.slow
def test_ingest_end_to_end_builds_index(make_pdf, tmp_path):
    pdf = make_pdf(
        "Farm_business_school_manual.pdf",
        [("Farm Business School teaches farmers to record every expense and every sale "
          "so that net income can be computed at the end of the season. ") * 6,
         ("A simple cash book has columns for the date, the item, money in, and money out. "
          "Totals are carried forward each week. ") * 6],
    )
    cfg = RagConfig(index_dir=tmp_path / "idx", chunk_size=500, chunk_overlap=50)
    manifest = ingest(cfg, sources=[pdf], rebuild=True)

    assert manifest["embedding_model"] == cfg.embedding_model
    assert manifest["documents"]["Farm_business_school_manual"]["chunks"] > 0
    assert (cfg.index_dir / "manifest.json").exists()
    saved = json.loads((cfg.index_dir / "manifest.json").read_text())
    assert saved["documents"] == manifest["documents"]

    from rag.store import ChunkStore

    store = ChunkStore(cfg.index_dir, cfg.collection_name)
    assert store.count() == manifest["documents"]["Farm_business_school_manual"]["chunks"]
    hits = store.query(
        __import__("rag.embeddings", fromlist=["Embedder"]).Embedder(cfg.embedding_model).embed_one(
            "how do I record farm expenses"
        ),
        top_k=2,
    )
    assert hits and hits[0].score > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest rag/tests/test_ingest.py -v`
Expected: FAIL with `ImportError` on `rag.ingest`.

- [ ] **Step 4: Write minimal implementation**

`rag/ingest.py`:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from rag.chunking import PageText, chunk_pages
from rag.config import RagConfig

RAW_DIR = Path("data/raw")
MIN_PAGE_CHARS = 100

DOC_TITLES: dict[str, str] = {
    "BAFS_explanatory_manual": (
        "Explanatory Manual — PNS Code of GAP for Fruits and Vegetable Farming"
    ),
    "Farm_business_school_manual": "Farm Business School Manual",
    "PAFES_manual_of_operations": "PAFES Manual of Operations",
}

_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_INLINE_WS = re.compile(r"[ \t]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def clean_page(text: str) -> str:
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _INLINE_WS.sub(" ", text)
    text = _MANY_NEWLINES.sub("\n\n", text)
    return text.strip()


def detect_running_lines(pages: list[str], *, min_fraction: float = 0.5) -> set[str]:
    counter: Counter[str] = Counter()
    for page in pages:
        seen = {ln.strip() for ln in page.splitlines() if 0 < len(ln.strip()) <= 80}
        counter.update(seen)
    threshold = max(3, int(len(pages) * min_fraction))
    return {line for line, count in counter.items() if count >= threshold}


def strip_running_lines(text: str, running: set[str]) -> str:
    kept = [line for line in text.splitlines() if line.strip() not in running]
    return "\n".join(kept).strip()


def extract_pages(pdf_path: Path) -> list[PageText]:
    from pypdf import PdfReader

    doc_id = pdf_path.stem
    title = DOC_TITLES.get(doc_id, doc_id)
    reader = PdfReader(str(pdf_path))
    return [
        PageText(doc_id=doc_id, doc_title=title, page_number=i, text=page.extract_text() or "")
        for i, page in enumerate(reader.pages, start=1)
    ]


def prepare_pages(raw_pages: list[PageText]) -> list[PageText]:
    cleaned = [clean_page(page.text) for page in raw_pages]
    running = detect_running_lines(cleaned)
    prepared: list[PageText] = []
    for page, text in zip(raw_pages, cleaned):
        stripped = strip_running_lines(text, running)
        if len(stripped) < MIN_PAGE_CHARS:
            continue
        prepared.append(
            PageText(
                doc_id=page.doc_id,
                doc_title=page.doc_title,
                page_number=page.page_number,
                text=stripped,
            )
        )
    return prepared


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ingest(
    cfg: RagConfig,
    *,
    sources: list[Path] | None = None,
    rebuild: bool = False,
) -> dict:
    from rag.embeddings import Embedder
    from rag.store import ChunkStore

    paths = sources if sources is not None else sorted(RAW_DIR.glob("*.pdf"))
    if not paths:
        raise SystemExit(f"no PDFs found in {RAW_DIR}")

    cfg.index_dir.mkdir(parents=True, exist_ok=True)
    embedder = Embedder(cfg.embedding_model)
    store = ChunkStore(cfg.index_dir, cfg.collection_name)
    if rebuild:
        store.reset()

    manifest: dict = {
        "embedding_model": cfg.embedding_model,
        "chunk_size": cfg.chunk_size,
        "chunk_overlap": cfg.chunk_overlap,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": {},
    }

    for path in paths:
        prepared = prepare_pages(extract_pages(path))
        chunks = chunk_pages(prepared, chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap)
        if not chunks:
            continue
        store.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=embedder.embed([c.text for c in chunks]),
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "doc_title": c.doc_title,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                }
                for c in chunks
            ],
        )
        manifest["documents"][path.stem] = {"chunks": len(chunks), "sha256": _sha256(path)}

    (cfg.index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest AgriWise source PDFs into the RAG index.")
    parser.add_argument("--source", dest="sources", action="append", type=Path)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args(argv)

    cfg = RagConfig.from_env()
    manifest = ingest(cfg, sources=args.sources, rebuild=args.rebuild)
    total = sum(doc["chunks"] for doc in manifest["documents"].values())
    print(
        f"ingested {total} chunks from {len(manifest['documents'])} document(s) -> {cfg.index_dir}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the fast tests, then the slow test**

Run: `uv run pytest rag/tests/test_ingest.py -v -m "not slow"`
Expected: PASS (4 fast tests).

Run: `uv run pytest rag/tests/test_ingest.py -v -m slow`
Expected: PASS (downloads the MiniLM model on first run — allow a minute).

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check rag/ingest.py rag/tests/test_ingest.py rag/tests/conftest.py
git add rag/ingest.py rag/tests/test_ingest.py rag/tests/conftest.py
git commit -m "feat: add offline pdf ingestion cli"
```

---

## Task 10: API request/response schemas

**Files:**
- Create: `apps/api/app/schemas/rag.py`
- Create: `apps/api/tests/test_rag_schemas.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.schemas.rag.ChatMessage` — `{role: Literal["user", "assistant"], content: str}` with `content` `min_length=1, max_length=4000`
  - `app.schemas.rag.RagQueryRequest` — `{question: str (min_length=1, max_length=2000), history: list[ChatMessage] = []}`
  - `app.schemas.rag.Citation` — `{doc_id: str, doc_title: str, page_start: int, page_end: int}`
  - `app.schemas.rag.RagQueryResponse` — `{answer: str, citations: list[Citation]}`

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_rag_schemas.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.rag import ChatMessage, RagQueryRequest, RagQueryResponse


def test_request_defaults_history_to_empty_list():
    req = RagQueryRequest(question="how to compost")
    assert req.history == []


def test_request_rejects_blank_question():
    with pytest.raises(ValidationError):
        RagQueryRequest(question="")


def test_request_rejects_overlong_question():
    with pytest.raises(ValidationError):
        RagQueryRequest(question="x" * 2001)


def test_chat_message_role_is_constrained():
    with pytest.raises(ValidationError):
        ChatMessage(role="system", content="nope")


def test_response_shape():
    resp = RagQueryResponse(
        answer="Record expenses in a cash book.",
        citations=[
            {"doc_id": "fbs", "doc_title": "Farm Business School Manual",
             "page_start": 88, "page_end": 89}
        ],
    )
    assert resp.citations[0].page_end == 89
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/api/tests/test_rag_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: app.schemas.rag`.

- [ ] **Step 3: Write minimal implementation**

`apps/api/app/schemas/rag.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


class Citation(BaseModel):
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest apps/api/tests/test_rag_schemas.py -v`
Expected: PASS (5).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check apps/api/app/schemas/rag.py apps/api/tests/test_rag_schemas.py
git add apps/api/app/schemas/rag.py apps/api/tests/test_rag_schemas.py
git commit -m "feat: add rag query api schemas"
```

---

## Task 11: API router, settings, and startup wiring

**Files:**
- Create: `apps/api/app/routers/rag.py`
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/.env.example`
- Create: `apps/api/tests/test_rag_router.py`

**Interfaces:**
- Consumes: `app.schemas.rag.*`, `app.config.get_settings`, `rag.pipeline.RagPipeline`, `rag.pipeline.RagAnswer`, `rag.prompt.ChatTurn`, `rag.generator.RagGenerationError`, `rag.config.RagConfig`
- Produces:
  - `app.config.Settings` gains: `embedding_model: str = "all-MiniLM-L6-v2"`, `rag_chunk_size: int = 500`, `rag_chunk_overlap: int = 50`, `rag_top_k: int = 4`, `rag_index_dir: str = "data/processed/rag_index"`, `rag_score_floor: float = 0.0`
  - `app.config.build_rag_config(settings: Settings) -> rag.config.RagConfig`
  - `app.routers.rag.router` — `APIRouter(prefix="/rag", tags=["rag"])` with `POST /query -> RagQueryResponse`
  - `app.routers.rag.get_pipeline(request: Request) -> RagPipeline` — dependency; raises `HTTPException(503)` when `request.app.state.rag_pipeline is None`
  - `app.main._build_rag_pipeline(settings) -> RagPipeline | None` — returns `None` (with a logged warning) when `<rag_index_dir>/manifest.json` is missing or the pipeline fails to build; logs a warning on embedding-model mismatch

- [ ] **Step 1: Write the failing test**

`apps/api/tests/test_rag_router.py`:

```python
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

    def answer(self, question, history=None):
        self.calls.append((question, len(history or [])))
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
    # no dependency override -> app.state.rag_pipeline is None at startup
    with TestClient(create_app()) as client:
        assert client.post("/rag/query", json={"question": "hello"}).status_code == 503
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest apps/api/tests/test_rag_router.py -v`
Expected: FAIL — `app.routers.rag` does not exist.

- [ ] **Step 3: Extend `app/config.py`**

Add fields to `Settings` (after `groq_model`) and a builder function at module end:

```python
    # RAG retrieval / ingestion
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 4
    rag_index_dir: str = "data/processed/rag_index"
    rag_score_floor: float = 0.0
```

```python
def build_rag_config(settings: Settings) -> "RagConfig":
    from pathlib import Path

    from rag.config import RagConfig

    return RagConfig(
        groq_api_key=settings.groq_api_key,
        groq_model=settings.groq_model,
        embedding_model=settings.embedding_model,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        top_k=settings.rag_top_k,
        index_dir=Path(settings.rag_index_dir),
        score_floor=settings.rag_score_floor,
    )
```

Add `from rag.config import RagConfig` under a `TYPE_CHECKING` guard, or just keep the local import shown above and drop the quotes. Keep the module import-light.

- [ ] **Step 4: Create `app/routers/rag.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas.rag import Citation, RagQueryRequest, RagQueryResponse
from rag.generator import RagGenerationError
from rag.prompt import ChatTurn

router = APIRouter(prefix="/rag", tags=["rag"])


def get_pipeline(request: Request):
    pipeline = getattr(request.app.state, "rag_pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline unavailable; run `uv run python -m rag.ingest` to build the index",
        )
    return pipeline


@router.post("/query", response_model=RagQueryResponse)
def query(payload: RagQueryRequest, pipeline=Depends(get_pipeline)) -> RagQueryResponse:
    if not pipeline.can_generate:
        raise HTTPException(
            status_code=503,
            detail="generation unavailable: GROQ_API_KEY not configured",
        )
    history = [ChatTurn(role=m.role, content=m.content) for m in payload.history]
    try:
        result = pipeline.answer(payload.question, history)
    except RagGenerationError as exc:
        raise HTTPException(status_code=503, detail=f"generation failed: {exc}") from exc
    return RagQueryResponse(
        answer=result.answer,
        citations=[Citation(**citation.model_dump()) for citation in result.citations],
    )
```

- [ ] **Step 5: Wire startup in `app/main.py`**

Add imports (`import json`, `import logging`, `from pathlib import Path`), a module logger, the builder, router inclusion, and populate `app.state` in `lifespan`:

```python
logger = logging.getLogger("agriwise.rag")


def _build_rag_pipeline(settings):
    from app.config import build_rag_config

    manifest_path = Path(settings.rag_index_dir) / "manifest.json"
    if not manifest_path.exists():
        logger.warning(
            "RAG index missing at %s; /rag/query returns 503. Run `uv run python -m rag.ingest`.",
            manifest_path.parent,
        )
        return None
    try:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("embedding_model") != settings.embedding_model:
            logger.warning(
                "RAG index embedding model %r != configured %r; rebuild with --rebuild.",
                manifest.get("embedding_model"),
                settings.embedding_model,
            )
        from rag.pipeline import RagPipeline

        return RagPipeline.from_config(build_rag_config(settings))
    except Exception:
        logger.exception("failed to build RAG pipeline; /rag/query returns 503")
        return None
```

In `lifespan`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_pipeline = _build_rag_pipeline(get_settings())
    yield
```

In `create_app`, after the health route:

```python
    from app.routers import rag as rag_router

    app.include_router(rag_router.router)
```

Also set `app.state.rag_pipeline = None` at the end of `create_app` (so `TestClient` used without the `with` block still has the attribute). The `lifespan` value wins when the app runs normally or under `with TestClient(...)`.

- [ ] **Step 6: Update `apps/api/.env.example`**

Append:

```
EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50
RAG_TOP_K=4
RAG_INDEX_DIR=data/processed/rag_index
RAG_SCORE_FLOOR=0.0
```

- [ ] **Step 7: Run tests**

Run: `uv run pytest apps/api/tests -v`
Expected: PASS — `test_rag_router.py` (5), `test_rag_schemas.py` (5), `test_health.py` (1).

- [ ] **Step 8: Lint and commit**

```bash
uv run ruff check apps/api
git add apps/api
git commit -m "feat: add POST /rag/query with startup-cached pipeline"
```

---

## Task 12: Web types and API client

**Files:**
- Create: `apps/web/src/types/rag.ts`
- Create: `apps/web/src/lib/rag.ts`
- Create: `apps/web/src/lib/rag.test.ts`

**Interfaces:**
- Consumes: `@/lib/api` (`apiFetch`, `ApiError`)
- Produces:
  - `@/types/rag`: `ChatRole = "user" | "assistant"`; `ChatMessage = { role: ChatRole; content: string }`; `Citation = { doc_id: string; doc_title: string; page_start: number; page_end: number }`; `RagQueryRequest = { question: string; history: ChatMessage[] }`; `RagQueryResponse = { answer: string; citations: Citation[] }`
  - `@/lib/rag`: `askAgriWise(question: string, history: ChatMessage[]): Promise<RagQueryResponse>` — POSTs `/rag/query`

- [ ] **Step 1: Write the failing test**

`apps/web/src/lib/rag.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { askAgriWise } from "@/lib/rag";

afterEach(() => vi.restoreAllMocks());

describe("askAgriWise", () => {
  it("posts question and history to /rag/query", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ answer: "hi", citations: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await askAgriWise("how to compost", [{ role: "user", content: "hello" }]);

    expect(result.answer).toBe("hi");
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/rag\/query$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      question: "how to compost",
      history: [{ role: "user", content: "hello" }],
    });
  });

  it("propagates ApiError on failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("no", { status: 503 })));
    await expect(askAgriWise("q", [])).rejects.toMatchObject({ status: 503 });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm run test -- rag`
Expected: FAIL — cannot resolve `@/lib/rag`.

- [ ] **Step 3: Write minimal implementation**

`apps/web/src/types/rag.ts`:

```ts
export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface Citation {
  doc_id: string;
  doc_title: string;
  page_start: number;
  page_end: number;
}

export interface RagQueryRequest {
  question: string;
  history: ChatMessage[];
}

export interface RagQueryResponse {
  answer: string;
  citations: Citation[];
}
```

`apps/web/src/lib/rag.ts`:

```ts
import { apiFetch } from "@/lib/api";
import type { ChatMessage, RagQueryResponse } from "@/types/rag";

export function askAgriWise(
  question: string,
  history: ChatMessage[],
): Promise<RagQueryResponse> {
  return apiFetch<RagQueryResponse>("/rag/query", {
    method: "POST",
    body: JSON.stringify({ question, history }),
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && npm run test -- rag`
Expected: PASS (2).

- [ ] **Step 5: Typecheck, lint, commit**

```bash
cd apps/web && npm run typecheck && npm run lint
cd ../.. && git add apps/web/src/types/rag.ts apps/web/src/lib/rag.ts apps/web/src/lib/rag.test.ts
git commit -m "feat(web): add rag api client and types"
```

---

## Task 13: Chat page

**Files:**
- Create: `apps/web/src/app/chat/page.tsx`
- Create: `apps/web/src/app/chat/page.test.tsx`
- Modify: `apps/web/src/app/page.tsx`

**Interfaces:**
- Consumes: `@/lib/rag` (`askAgriWise`), `@/types/rag` (`ChatMessage`, `Citation`)
- Produces: a client component default-exported from `apps/web/src/app/chat/page.tsx` mounted at `/chat`.

Behavior:
- Local state: `messages: Array<ChatMessage & { citations?: Citation[] }>`, `input: string`, `pending: boolean`, `error: string | null`.
- Submit (form): ignore empty/whitespace or while `pending`. Append `{role: "user", content}`, clear input, set `pending`. Call `askAgriWise(content, historyBeforeThisTurn)` where history is the prior `messages` mapped to `{role, content}`. On success append `{role: "assistant", content: answer, citations}`. On failure set `error` to a friendly string and leave the user message in place.
- Render: message list (user right-aligned, assistant left), each assistant message followed by a citation list rendered as `{doc_title} — p.{page_start}` (or `p.{start}-{end}`), deduped already by the server. Empty state: a heading + 2 example questions as buttons that fill the input. Pending: disabled input + "Thinking…" indicator. Error: inline red text with a "Try again" button that re-sends the last user message.
- Styling: Tailwind classes consistent with the scaffold; single-column, `max-w-2xl`, readable on mobile. No markdown rendering — render `content` with `whitespace-pre-wrap`.

- [ ] **Step 1: Write the failing test**

`apps/web/src/app/chat/page.test.tsx`:

```tsx
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import ChatPage from "@/app/chat/page";

vi.mock("@/lib/rag", () => ({ askAgriWise: vi.fn() }));
import { askAgriWise } from "@/lib/rag";

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

function ask(text: string) {
  fireEvent.change(screen.getByRole("textbox"), { target: { value: text } });
  fireEvent.submit(screen.getByTestId?.("chat-form") ?? screen.getByRole("form"));
}

describe("ChatPage", () => {
  it("renders the answer and its citations", async () => {
    vi.mocked(askAgriWise).mockResolvedValue({
      answer: "Keep a cash book.",
      citations: [
        { doc_id: "fbs", doc_title: "Farm Business School Manual", page_start: 88, page_end: 89 },
      ],
    });
    render(<ChatPage />);
    ask("how do I track expenses?");

    expect(await screen.findByText("Keep a cash book.")).toBeInTheDocument();
    expect(screen.getByText(/Farm Business School Manual — p\.88-89/)).toBeInTheDocument();
    expect(vi.mocked(askAgriWise).mock.calls[0][0]).toBe("how do I track expenses?");
    expect(vi.mocked(askAgriWise).mock.calls[0][1]).toEqual([]);
  });

  it("shows an error with retry when the request fails", async () => {
    vi.mocked(askAgriWise).mockRejectedValueOnce(new Error("boom"));
    render(<ChatPage />);
    ask("hello");

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();

    vi.mocked(askAgriWise).mockResolvedValueOnce({ answer: "recovered", citations: [] });
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("recovered")).toBeInTheDocument();
  });

  it("disables input while pending", async () => {
    let resolve!: (v: unknown) => void;
    vi.mocked(askAgriWise).mockReturnValue(new Promise((r) => (resolve = r)) as never);
    render(<ChatPage />);
    ask("slow one");

    await waitFor(() => expect(screen.getByRole("textbox")).toBeDisabled());
    resolve({ answer: "done", citations: [] });
    expect(await screen.findByText("done")).toBeInTheDocument();
  });
});
```

Note: use a `data-testid="chat-form"` on the `<form>` and `aria-label` so the test can find it; adjust the helper to `screen.getByTestId("chat-form")` and drop the fallback if preferred.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && npm run test -- chat`
Expected: FAIL — cannot resolve `@/app/chat/page`.

- [ ] **Step 3: Write minimal implementation**

`apps/web/src/app/chat/page.tsx`:

```tsx
"use client";

import { useState } from "react";

import { askAgriWise } from "@/lib/rag";
import type { Citation } from "@/types/rag";

type Turn = { role: "user" | "assistant"; content: string; citations?: Citation[] };

const EXAMPLES = [
  "How do I record farm expenses in a Farm Business School?",
  "What are the key requirements of the Code of GAP for vegetables?",
];

function pageLabel(c: Citation): string {
  return c.page_start === c.page_end
    ? `${c.doc_title} — p.${c.page_start}`
    : `${c.doc_title} — p.${c.page_start}-${c.page_end}`;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(question: string, history: Turn[]) {
    setPending(true);
    setError(null);
    try {
      const res = await askAgriWise(
        question,
        history.map((m) => ({ role: m.role, content: m.content })),
      );
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, citations: res.citations },
      ]);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setPending(false);
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || pending) return;
    const history = messages;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    void send(question, history);
  }

  function retry() {
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    const history = messages.slice(
      0,
      messages.findIndex((m) => m === lastUser),
    );
    void send(lastUser.content, history);
  }

  return (
    <main className="mx-auto flex min-h-full max-w-2xl flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-semibold">Ask AgriWise</h1>

      {messages.length === 0 && (
        <div className="flex flex-col gap-2 text-slate-600 dark:text-slate-300">
          <p>Ask about the DA farm-business and good-agricultural-practice manuals.</p>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              className="rounded border border-slate-300 px-3 py-2 text-left text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
              onClick={() => setInput(ex)}
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      <ul className="flex flex-col gap-3">
        {messages.map((m, i) => (
          <li
            key={i}
            className={m.role === "user" ? "self-end text-right" : "self-start"}
          >
            <div
              className={`whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                m.role === "user"
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-100 dark:bg-slate-800"
              }`}
            >
              {m.content}
            </div>
            {m.citations && m.citations.length > 0 && (
              <ul className="mt-1 text-xs text-slate-500">
                {m.citations.map((c, j) => (
                  <li key={j}>{pageLabel(c)}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>

      {pending && <p className="text-sm text-slate-500">Thinking…</p>}
      {error && (
        <p className="text-sm text-red-600">
          {error}{" "}
          <button type="button" className="underline" onClick={retry}>
            Try again
          </button>
        </p>
      )}

      <form
        data-testid="chat-form"
        aria-label="Ask AgriWise"
        onSubmit={onSubmit}
        className="mt-auto flex gap-2"
      >
        <input
          type="text"
          value={input}
          disabled={pending}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
        />
        <button
          type="submit"
          disabled={pending}
          className="rounded bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 4: Add a link from the landing page**

In `apps/web/src/app/page.tsx`, add inside `<main>` after the paragraph:

```tsx
      <a href="/chat" className="text-emerald-700 underline dark:text-emerald-400">
        Ask AgriWise →
      </a>
```

- [ ] **Step 5: Run tests**

Run: `cd apps/web && npm run test`
Expected: PASS — `chat/page.test.tsx` (3), `lib/rag.test.ts` (2), `lib/api.test.ts` (2).

- [ ] **Step 6: Typecheck, lint, build**

Run: `cd apps/web && npm run typecheck && npm run lint && npm run build`
Expected: all clean; `/chat` shows in the route list.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/app/chat apps/web/src/app/page.tsx
git commit -m "feat(web): add multi-turn Ask AgriWise chat page"
```

---

## Task 14: Documentation and end-to-end verification

**Files:**
- Modify: `README.md`
- Create: `apps/api/README.md`
- Modify: `apps/api/.env.example` (verify from Task 11)

**Interfaces:** none (docs only).

- [ ] **Step 1: Add a RAG section to the root `README.md`**

Under "Development", add:

````markdown
### RAG chatbot (Ask AgriWise)

The chatbot answers from the three DA manuals in `data/raw/`. Build the index once:

```powershell
uv sync
uv run python -m rag.ingest --rebuild
```

This writes a Chroma index to `data/processed/rag_index/` (gitignored). The API loads it at
startup; without it, `POST /rag/query` returns 503. Generation needs `GROQ_API_KEY` in
`apps/api/.env` (model `openai/gpt-oss-120b`).
````

Add `POST /rag/query` to the API endpoints table with purpose "Ask AgriWise chatbot (document-grounded, multi-turn)".

- [ ] **Step 2: Create `apps/api/README.md`**

```markdown
# AgriWise API

FastAPI backend. Part of the repo-root uv project — run all commands from the repo root.

## Run

```powershell
uv sync
cp apps/api/.env.example apps/api/.env   # then set GROQ_API_KEY
uv run python -m rag.ingest --rebuild    # build the RAG index (first time / after source changes)
uv run uvicorn app.main:app --reload
```

## Test

```powershell
uv run pytest                 # all Python tests
uv run pytest -m "not slow"   # skip the end-to-end ingestion test
uv run ruff check .
```

## Endpoints

- `GET /health`
- `POST /rag/query` — `{ question, history[] }` → `{ answer, citations[] }`; 503 if the index is
  missing or `GROQ_API_KEY` is unset.
```

- [ ] **Step 3: Full Python verification**

```bash
uv run pytest -m "not slow"
uv run pytest -m slow
uv run ruff check .
```
Expected: all PASS, ruff clean.

- [ ] **Step 4: Full web verification**

```bash
cd apps/web && npm run test && npm run lint && npm run typecheck && npm run build
```
Expected: all PASS/clean.

- [ ] **Step 5: Manual smoke test**

```bash
uv run python -m rag.ingest --rebuild
# expect: "ingested N chunks from 3 document(s) -> data/processed/rag_index"
uv run uvicorn app.main:app &
curl -s localhost:8000/rag/query -H 'content-type: application/json' \
  -d '{"question":"How do I record farm expenses?","history":[]}' | python -m json.tool
# expect: JSON with a non-empty "answer" and at least one citation
```
In a second terminal: `cd apps/web && npm run dev`, open `http://localhost:3000/chat`, ask a
question, confirm the answer and citations render and a follow-up question keeps context.

- [ ] **Step 6: Commit**

```bash
git add README.md apps/api/README.md apps/api/.env.example
git commit -m "docs: document the RAG chatbot setup and endpoints"
```

---

## Self-Review Notes

**Spec coverage:**
- §3 config → Task 1 (`RagConfig`), Task 11 (`Settings` + `.env.example`)
- §4 packaging → Task 1
- §5 module layout → Tasks 2–13 (every file listed)
- §6 ingestion → Task 9
- §7 retriever → Task 5
- §8 prompt (incl. analytics seam) → Task 6
- §9 generator (incl. missing-key 503 path) → Task 7, Task 11
- §10 pipeline (citation dedup) → Task 8
- §11 API contract (200/422/503, history cap) → Tasks 10–11; history cap enforced in `build_messages` (Task 6, `test_history_is_trimmed_to_max_turns`)
- §12 chat page → Task 13
- §13 startup wiring (manifest check, model-mismatch warning) → Task 11 (`_build_rag_pipeline`)
- §14 testing → every task's tests + Task 14 verification
- §15 out of scope → `analytics_context` parameter present but unused (Task 6); no streaming/persistence
- §16 risks → model download called out in Tasks 1, 9, 14

**Type consistency:** `RetrievedChunk`, `Chunk`, `PageText`, `StoredChunk`, `ChatTurn`, `Citation`, `RagAnswer` names and fields are identical everywhere referenced. API `ChatMessage` ↔ `rag` `ChatTurn` mapping is explicit in Task 11 Step 4. `askAgriWise(question, history)` signature matches between Task 12 definition and Task 13 use.

**Placeholder scan:** no TBD / "handle errors" / "similar to" — every code step is complete.

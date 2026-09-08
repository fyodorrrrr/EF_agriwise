# RAG Pipeline — Document-Only Baseline

**Date:** 2026-09-08
**Status:** Design — pending review
**Scope:** Sprint 1 RAG baseline (M08). Document-only retrieval and generation. Structured
analytics-context injection is explicitly deferred to Sprint 5; this design leaves a seam for it
but does not build it.

## 1. Goal

Give AgriWise a grounded "Ask AgriWise" chatbot that answers questions from three Philippine
Department of Agriculture extension manuals, with source citations, over a multi-turn
conversation. The pipeline must run entirely offline for ingestion and retrieval; only answer
generation calls an external service (Groq).

## 2. Sources

Three digital-text PDFs in `data/raw/` (read-only; never modified in place):

| File | Pages | Content |
|---|---|---|
| `BAFS_explanatory_manual.pdf` | 148 | Explanatory Manual for the PNS Code of GAP, Fruits & Vegetable Farming |
| `Farm_business_school_manual.pdf` | 244 | Farm Business School curriculum and facilitation |
| `PAFES_manual_of_operations.pdf` | 147 | Province-led Agriculture and Fisheries Extension Systems, manual of operations |

All three extract cleanly with `pypdf` (verified) — no OCR needed.

## 3. Configuration

Read from environment / `.env` via the existing `app/config.py` settings object. New keys:

| Key | Default | Meaning |
|---|---|---|
| `GROQ_API_KEY` | — (required for generation) | Groq credential |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq chat model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model id |
| `RAG_CHUNK_SIZE` | `500` | chunk target size, **characters** |
| `RAG_CHUNK_OVERLAP` | `50` | overlap between consecutive chunks, **characters** |
| `RAG_TOP_K` | `4` | chunks retrieved per query |
| `RAG_INDEX_DIR` | `data/processed/rag_index` | Chroma persistence directory |
| `RAG_SCORE_FLOOR` | `0.0` | minimum similarity to include a chunk (0 = keep all top-k) |

Character-based chunking keeps every chunk under MiniLM's 256-token input limit, so each chunk
embeds fully.

## 4. Packaging

Consolidate all Python into **one uv project rooted at the repo root**, exposing two flat,
independently testable packages: `rag` (RAG pipeline) and `app` (FastAPI backend). One virtual
environment, one lockfile — right-sized for a hackathon and keeps `rag/` a flat directory.

- Root `pyproject.toml`: project `agriwise`, Python `>=3.12`. Runtime deps: `fastapi`,
  `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `pypdf`, `sentence-transformers`,
  `chromadb`, `groq`. Dev deps: `pytest`, `httpx`, `ruff`, `reportlab` (test-fixture PDFs).
- Hatchling build exposing both packages:
  ```toml
  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"

  [tool.hatch.build.targets.wheel]
  packages = ["rag", "apps/api/app"]
  ```
  `uv sync` editable-installs the root project, so `import rag` and `import app` resolve from
  anywhere in the repo — no `sys.path` shims, no `--app-dir`.
- Root `[tool.pytest.ini_options] testpaths = ["apps/api/tests", "rag/tests"]`.
- The pre-existing `apps/api/pyproject.toml`, `apps/api/uv.lock`, and `apps/api/.python-version`
  from the scaffold are removed; `.python-version` moves to the repo root.
- `ml/` and `markets/` are not added as packages in this change.

Commands (all from the repo root):

```powershell
uv sync
uv run python -m rag.ingest --rebuild
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
```

## 5. Module Layout

```
rag/                   # flat package, importable as `rag`
├── __init__.py
├── config.py          # RagConfig dataclass, built from env or passed explicitly
├── ingest.py          # offline CLI: python -m rag.ingest
├── chunking.py        # pure text -> list[Chunk] with metadata
├── embeddings.py      # thin cached wrapper around SentenceTransformer
├── store.py           # Chroma collection open/create, upsert, query
├── retriever.py       # Retriever: query text -> list[RetrievedChunk]
├── prompt.py          # build_messages(question, history, retrieved) -> list[dict]
├── generator.py       # Generator: messages -> answer string (Groq)
└── pipeline.py        # RagPipeline: ties retriever + prompt + generator; returns RagAnswer

apps/api/app/          # flat package, importable as `app`
├── config.py          # + RAG settings and build_rag_config(settings)
├── routers/rag.py     # POST /rag/query
├── schemas/rag.py     # RagQueryRequest, RagQueryResponse, Citation, ChatMessage
└── main.py            # lifespan: build RagPipeline once, store on app.state

apps/web/src/
├── app/chat/page.tsx  # multi-turn chat UI
├── lib/rag.ts         # typed client for POST /rag/query
└── types/rag.ts       # request/response types mirroring schemas/rag.py

rag/tests/  and  apps/api/tests/   # pytest suites
```

## 6. Ingestion Pipeline (`rag/ingest.py`)

Offline, idempotent, run manually: `uv run python -m rag.ingest` (optionally
`--source <file>`, `--rebuild`).

Steps:

1. **Enumerate** PDFs in `data/raw/` (or the `--source` file).
2. **Extract** per page with `pypdf`: `(doc_id, doc_title, page_number, raw_text)`.
   `doc_id` is the filename stem; `doc_title` is a hardcoded human-readable map for the three
   known files, falling back to the stem.
3. **Clean** each page:
   - normalize whitespace, de-hyphenate line-break splits (`agri-\nculture` -> `agriculture`);
   - drop pages whose cleaned text is < 100 chars (covers blank / divider pages);
   - strip repeated running headers/footers detected as identical short lines recurring on
     many pages of the same document.
4. **Chunk** (`chunking.py`): concatenate a document's cleaned pages into one stream while
   tracking page offsets; split into ~`RAG_CHUNK_SIZE`-char windows with `RAG_CHUNK_OVERLAP`
   overlap, preferring to break on paragraph then sentence then whitespace boundaries near the
   target size. Each `Chunk` carries: `chunk_id` (`<doc_id>::<running_index>`), `doc_id`,
   `doc_title`, `page_start`, `page_end`, `text`.
5. **Embed** all chunk texts with `embeddings.py` (batched).
6. **Persist** to Chroma at `RAG_INDEX_DIR`: collection `agriwise_docs`, one record per chunk
   (`id=chunk_id`, `document=text`, `embedding`, `metadata={doc_id, doc_title, page_start,
   page_end}`). `--rebuild` deletes the collection first; default run upserts by `chunk_id`.
7. **Write** `data/processed/rag_index/manifest.json`: embedding model id, chunk params,
   per-document chunk counts, source file sha256, ingest timestamp. Used to detect a
   stale/mismatched index at API startup (log a warning; do not crash).

The `data/processed/rag_index/` directory is gitignored; the corpus is rebuilt from
`data/raw/` by anyone running the script.

## 7. Retriever (`rag/retriever.py`)

```python
class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_title: str
    page_start: int
    page_end: int
    text: str
    score: float          # cosine similarity in [0, 1]

class Retriever:
    def __init__(self, store, embedder, top_k: int, score_floor: float): ...
    def retrieve(self, query: str) -> list[RetrievedChunk]: ...
```

- Embeds the query with the same model, queries Chroma for `top_k`, converts Chroma distance
  to a similarity score, drops anything below `score_floor`, returns in descending score order.
- Constructed once at API startup; holds the loaded model and open collection.

## 8. Prompt (`rag/prompt.py`)

```python
def build_messages(
    question: str,
    history: list[ChatTurn],          # prior user/assistant turns, already trimmed
    retrieved: list[RetrievedChunk],
    analytics_context: str | None = None,   # SEAM: always None in this sprint
) -> list[dict]:
```

- **System message** establishes the AgriWise persona: an assistant for CALABARZON smallholder
  farmers and extension workers; answers only from the provided manual excerpts; cites sources;
  says it does not know when the excerpts do not cover the question; does not give medical,
  legal, or pesticide-dosage advice and refers those to a local agricultural technician or the
  Department of Agriculture.
- **Context block**: the retrieved chunks, each prefixed with a bracketed tag
  `[<doc_title>, p.<page_start>(–<page_end>)]`, instructing the model to cite using those tags.
- `analytics_context`, when non-None (Sprint 5), is rendered as a *separate* labeled block
  ahead of the document context. In this sprint the parameter exists but is never passed.
- History is appended as prior turns between system and the current user question; the caller
  passes at most the last `N` turns (default 6) to bound prompt size.

## 9. Generator (`rag/generator.py`)

```python
class Generator:
    def __init__(self, api_key: str, model: str, timeout_s: float = 30): ...
    def generate(self, messages: list[dict]) -> str: ...
```

- Wraps the `groq` client, non-streaming, `temperature=0.2`.
- Raises `RagGenerationError` on Groq failure/timeout; the router maps it to `503`.
- If `api_key` is missing the pipeline is built without a generator and the router returns
  `503` with `{"detail": "generation unavailable: GROQ_API_KEY not configured"}`. Retrieval
  still works and is covered by tests.

## 10. Pipeline (`rag/pipeline.py`)

```python
class RagAnswer(BaseModel):
    answer: str
    citations: list[Citation]       # deduped, only chunks actually retrieved
    used_chunk_ids: list[str]

class RagPipeline:
    @classmethod
    def from_config(cls, cfg: RagConfig) -> "RagPipeline": ...
    def answer(self, question: str, history: list[ChatTurn]) -> RagAnswer: ...
```

`ChatTurn` is the `rag/` package's `{role: "user" | "assistant", content: str}` model; the API's
`ChatMessage` schema is the same shape and the router maps one to the other.

`Citation` = `{doc_id, doc_title, page_start, page_end}`. Citations are derived from the
retrieved set (every retrieved chunk yields a citation, deduped by `(doc_id, page_start,
page_end)`), not parsed out of the model text — simpler and can't hallucinate a page.

## 11. API Contract

`POST /rag/query`

```jsonc
// request
{
  "question": "How do I record farm expenses in a Farm Business School?",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
// response 200
{
  "answer": "…",
  "citations": [
    { "doc_id": "Farm_business_school_manual",
      "doc_title": "Farm Business School Manual",
      "page_start": 88, "page_end": 89 }
  ]
}
```

- `question`: 1–2000 chars, required. `history`: optional, default `[]`, server keeps only the
  last 6 turns, each `content` capped at 4000 chars.
- `503` when generation is unavailable (no key) or Groq errors.
- `422` on validation failure (FastAPI default).
- No auth, no rate limiting, no persistence of conversations (per global constraints).

Pydantic schemas live in `apps/api/app/schemas/rag.py`; TypeScript mirror in
`apps/web/src/types/rag.ts` with a fixture used by a frontend test.

## 12. Chat Page (`apps/web/src/app/chat/page.tsx`)

- Client component. Local state: `messages: ChatMessage[]`, `input`, `pending`, `error`.
- On submit: append the user message, POST `{ question, history }` via `lib/rag.ts`, append the
  assistant answer, render its citations as a small list beneath the bubble
  (`Doc Title — p. N`).
- States: empty (a one-line prompt + 2–3 example questions), pending (disabled input +
  indicator), error (inline retry), normal.
- No streaming, no markdown rendering beyond line breaks in this sprint. Styling follows the
  scaffold's Tailwind setup; keep it minimal and readable on mobile.
- Reachable at `/chat`; a nav entry is added wherever the scaffold keeps navigation.

## 13. Startup Wiring (`apps/api/app/main.py`)

- In `lifespan`: if `RAG_INDEX_DIR` exists and its manifest matches the configured embedding
  model, build `RagPipeline.from_config(...)` and set `app.state.rag_pipeline`. Otherwise log a
  clear warning and set it to `None`.
- The router dependency returns `app.state.rag_pipeline` or raises `503` if `None`.
- Model load (~90 MB MiniLM) happens once at startup, not per request.

## 14. Testing

**Python (`rag/tests/` + `apps/api/tests/`):**

| Test file | Covers |
|---|---|
| `rag/tests/test_chunking.py` | size/overlap honored, boundary preference, page-range tracking, tiny-page drop |
| `rag/tests/test_store.py` | upsert + query round-trip on a temp Chroma dir with fake vectors |
| `rag/tests/test_retriever.py` | top-k ordering, score-floor filtering, metadata passthrough (fake embedder) |
| `rag/tests/test_prompt.py` | system rules present, citation tags on every chunk, history trimming, analytics block absent when `None` and present/separate when passed |
| `rag/tests/test_pipeline.py` | end-to-end with fake retriever + fake generator: citations deduped, `used_chunk_ids` correct |
| `apps/api/tests/test_rag_router.py` | 200 shape, 422 on bad input, 503 when pipeline `None`, history cap enforced; pipeline is a stub via dependency override |

No test calls Groq or downloads the model — `Generator` and the embedder are faked/injected.
One optional, marked-slow integration test can run real ingestion over a single-page synthetic
PDF.

**Frontend (`apps/web/src/`):**

| Test | Covers |
|---|---|
| `src/lib/rag.test.ts` | request body shape, error surfaces `ApiError` |
| `src/app/chat/page.test.tsx` | send flow renders answer + citations (fetch mocked), pending disables input, error shows retry |

**Manual verification (documented in the completion report):**

```powershell
# from repo root
uv run python -m rag.ingest --rebuild
uv run pytest rag/tests apps/api/tests/test_rag_router.py
uv run ruff check rag apps/api
cd apps/web; npm run test; npm run lint; npm run typecheck; npm run build
# then: uv run uvicorn app.main:app  +  npm run dev  ->  ask a question at /chat
```

## 15. Out of Scope (deferred to Sprint 5)

- Resolving commodity/province/view/market and injecting forecast values, verdicts, units, and
  opportunity breakdown into the prompt.
- Provenance rules (observed vs predicted vs proxy vs benchmarked), the "not observed
  consumption" demand disclosure, and refusal logic for missing red-onion / opportunity data.
- Streaming responses; markdown rendering; conversation persistence.

The `analytics_context` parameter in `build_messages` and a `RagPipeline.answer` signature that
can later accept a resolved-context object are the only forward accommodations made now.

## 16. Risks

- **MiniLM download at first run.** `sentence-transformers` fetches the model on first use;
  ingestion and API startup need one-time network access. Documented in the API README and the
  Sprint 6 "unavailable external prerequisites" note.
- **500-char chunks are small.** Precise but low-context passages. Acceptable for a demo; the
  chunk params are env-tunable without code change if answers feel thin.
- **Groq model string.** `openai/gpt-oss-120b` must be a valid Groq model id at demo time; the
  503 path keeps the rest of the app usable if it is deprecated.
- **Index/config drift.** Changing `EMBEDDING_MODEL` or chunk params requires
  `--rebuild`; the manifest check warns but cannot force it.

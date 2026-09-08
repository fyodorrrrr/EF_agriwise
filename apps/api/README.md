# AgriWise API

FastAPI backend. Part of the repo-root `uv` project — run all commands from the repo root.

## Run

```powershell
uv sync
copy apps\api\.env.example apps\api\.env   # then set GROQ_API_KEY (model openai/gpt-oss-120b)
uv run python -m rag.ingest --rebuild      # build the RAG index (first time / after data/raw/ changes)
uv run uvicorn app.main:app --reload
```

On macOS/Linux use `cp apps/api/.env.example apps/api/.env` instead of `copy`.

The RAG index is rebuilt from the PDFs in `data/raw/` and written to `data/processed/rag_index/`
(gitignored). Chunk size and overlap (`RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`) are measured in
characters. Without the index, `POST /rag/query` returns 503.

## Test

```powershell
uv run pytest                 # all Python tests
uv run pytest -m "not slow"   # skip the end-to-end ingestion test
uv run pytest -m slow         # only the end-to-end ingestion test
uv run ruff check .
```

## Endpoints

- `GET /health`
- `POST /rag/query` — `{ question, history[] }` -> `{ answer, citations[] }`; returns 503 if the
  RAG index is missing or `GROQ_API_KEY` is unset.

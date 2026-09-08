# AgriWise

Province-resolution demand, supply, price, and opportunity analytics for CALABARZON agriculture (Rice, Tomato, Red Onion, Banana), served from a FastAPI backend to a Next.js frontend.

## Architecture

FastAPI loads the versioned `ml/artifacts/` bundle once at startup and exposes province-resolution analytics through typed contracts consumed by the Next.js app.

- **Demand** — a committed quarterly **demand-pressure index** (FIES baseline + LFS activity + seasonal indices) for all four commodities. The optional rice FIES/XGBoost MT benchmark is deferred (see `docs/architecture/adr-001-rice-fies-xgboost-benchmark.md`).
- **Supply / Price** — observed history + a short forecast from `ml/artifacts/prepared/*_features.csv`: the learned model where a joblib is present, else seasonal-naive.
- **Opportunity** — peer-relative 0–100 score across the five provinces, config-driven (`ml/artifacts/config/opportunity_scoring_config.json`); no subtraction of incompatible units.
- **Markets** — curated public markets ranked by proximity, size proxy, coordinate confidence, and analytics support.
- **Ask AgriWise** — RAG over the DA manuals; injects the trusted analytics context for the current commodity/province selection.

## Status

| Module | State |
|---|---|
| Setup · Dashboard · Forecasting (+ Why this result?) | working |
| `/forecast/{catalog,outlook,evidence,methodology}` | working |
| Opportunity scoring | working |
| Model Evidence page | working |
| Curated Markets (`/markets`, `/markets/rank`) + page | working |
| Mapping — province analytics list + boundary map | working (on-map choropleth is a follow-up) |
| Ask AgriWise with analytics context | working (needs `GROQ_API_KEY` for generation) |
| Optional rice MT benchmark / `supply_gap_mt` | deferred (ADR-001) |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Pydantic, pandas, NumPy, scikit-learn/joblib, XGBoost, pytest
- **Frontend:** Next.js 16 (App Router), React, TypeScript, Tailwind CSS 4, Vitest

## Folder Structure

```
apps/
├── web/                 # Next.js frontend
└── api/                 # FastAPI backend
ml/
└── forecasting/         # Demand forecasting
markets/                 # Curated market directory + farmer-relative ranking
rag/                     # RAG pipeline
data/
├── raw/                 # Raw datasets — never modified in place
└── processed/           # Derived datasets
docs/
└── architecture/        # Architecture documentation
infra/
└── docker/              # Docker and infrastructure configuration
```

## Domain Constraints

These rules bind the code and its contracts:

- Supported commodities: Rice, Tomato, Red Onion, Banana.
- Analytics are province-resolution. Municipality selection may resolve to a province but is never presented as a municipality forecast.
- Demand is labeled **Estimated Demand Proxy**, never described as observed consumption.
- Supply: quarterly, metric tons. Price: monthly, PHP/kg. Demand: quarterly.
- Verdict vocabulary: `PASS`, `CAUTION`, `INSUFFICIENT_DATA`, and demand-specific `USABLE_PROXY` / `INDICATIVE_PROXY`.
- `INSUFFICIENT_DATA` components carry no forecast values; missing critical inputs block opportunity scoring.
- Do not modify `data/raw/` in place — derived inputs go in `data/processed/`.
- Out of scope: authentication, marketplace listings, buyer-demand volumes, transactions, admin CRUD.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /forecast/catalog` | Commodity/province catalog for setup and filters |
| `GET /forecast/outlook?commodity=&province=` | Demand/supply/price/opportunity outlook |
| `GET /forecast/evidence` | Model evidence per commodity/component |
| `GET /forecast/methodology` | Methodology registry + opportunity configuration + disclaimers |
| `POST /rag/query` | Ask AgriWise chatbot; optional `commodity`/`province` selectors inject the trusted analytics context |
| `GET /markets` · `GET /markets/rank?commodity=&province=` | Curated market directory and farmer-relative ranking |

## Development

```powershell
# Backend (from repo root)
uv run pytest                 # apps/api/tests, rag/tests, ml/demand/tests
uv run ruff check apps/api/app ml/forecasting rag markets

# Frontend
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
```

### RAG chatbot (Ask AgriWise)

The chatbot answers from the three DA manuals in `data/raw/`. Build the index once:

```powershell
uv sync
uv run python -m rag.ingest --rebuild
```

The ingester chunks the source PDFs (chunk size and overlap are measured in characters) and
writes a Chroma index to `data/processed/rag_index/` (gitignored). Rebuild it from `data/raw/`
with `uv run python -m rag.ingest --rebuild` whenever the source manuals change. The API loads the index
at startup; without it, `POST /rag/query` returns 503. Generation needs `GROQ_API_KEY` in
`apps/api/.env` (model `openai/gpt-oss-120b`).

## Documentation

- [`docs/architecture/Sprints_plan.md`](docs/architecture/Sprints_plan.md) — MVP completion plan, module status, and per-sprint scope.
- [`docs/demo-and-qa.md`](docs/demo-and-qa.md) — demo matrix, end-to-end journey, and release-evidence commands.
- [`docs/architecture/adr-001-rice-fies-xgboost-benchmark.md`](docs/architecture/adr-001-rice-fies-xgboost-benchmark.md) — why the optional rice MT benchmark is deferred.

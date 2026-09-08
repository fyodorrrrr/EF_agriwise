
# AgriWise

Province-resolution demand, supply, price, and opportunity analytics for CALABARZON agriculture (Rice, Tomato, Red Onion, Banana), served from a FastAPI backend to a Next.js frontend.

## Architecture

FastAPI loads a versioned forecasting snapshot once at startup and exposes province-resolution analytics through typed contracts consumed by the Next.js app.

- **Demand** — prepared proxy path for all commodities; optional FIES/XGBoost benchmark path for rice.
- **Supply / Price** — validated component artifacts (learned models or seasonal-naive history).
- **Opportunity** — normalized peer-relative inputs; no subtraction of incompatible units.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Pydantic, pandas, NumPy, scikit-learn/joblib, optional XGBoost, pytest
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
- Verdict vocabulary: `PASS`, `CAUTION`, `INSUFFICIENT_DATA`, and demand-specific `USABLE_PROXY`.
- `INSUFFICIENT_DATA` components carry no forecast values; missing critical inputs block opportunity scoring.
- Do not modify `data/raw/` in place — derived inputs go in `data/processed/`.
- Out of scope: authentication, marketplace listings, buyer-demand volumes, transactions, admin CRUD.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /forecast/catalog` | Commodity/province catalog for setup and filters |
| `GET /forecast/outlook?commodity=&province=` | Demand/supply/price/opportunity outlook |
| `GET /forecast/evidence` | Model evidence per commodity/component |
| `GET /forecast/methodology` | Methodology and opportunity configuration |
| `POST /rag/query` | Chatbot query |
| `/markets/*` | Curated market registry and ranking |

## Development

```powershell
# Backend
pytest
ruff check apps/api ml rag markets tests

# Frontend
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
```

## Documentation

- [`docs/architecture/Sprints_plan.md`](docs/architecture/Sprints_plan.md) — MVP completion plan, module status, and per-sprint scope.

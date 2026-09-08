# AgriWise MVP Completion Sprint Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the AgriWise hackathon MVP from the repository's current working baseline while keeping demand, supply, price, and opportunity outputs scientifically honest and consistent across the dashboard, forecasting, mapping, markets, evidence, and chatbot experiences.

**Architecture:** FastAPI loads the versioned forecasting snapshot once, exposes province-resolution analytics through typed contracts, and supplies those contracts to a Next.js application. Demand has a committed proxy path for all commodities and an optional FIES/XGBoost benchmark path for rice; supply and price use their validated component artifacts; opportunity combines normalized peer-relative inputs without subtracting incompatible units.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pandas, NumPy, scikit-learn/joblib, optional XGBoost, pytest, Next.js 16 App Router, React, TypeScript, Tailwind CSS 4, Vitest.

**Specs and evidence:** `docs/architecture/sprint-0-audit.md`, `docs/architecture/fies-demand-benchmark-pipeline.md`, `CODEBASE_CONTEXT.md`, `ml/artifacts/reports/unified_deployment_summary.csv`, and the checked-in contracts under `apps/api/app/schemas/` and `apps/web/src/types/`.

## Global Constraints

- Supported commodities are Rice, Tomato, Red Onion, and Banana.
- Forecast analytics are province-resolution. Municipality selection may resolve to a province but must never be presented as a municipality forecast.
- Demand must be labeled **Estimated Demand Proxy** and must never be described as observed commodity consumption.
- Supply remains quarterly in metric tons; price remains monthly in PHP/kg; demand remains quarterly.
- Preserve the verdicts in the current artifact bundle: `PASS`, `CAUTION`, `INSUFFICIENT_DATA`, and demand-specific `USABLE_PROXY`.
- `INSUFFICIENT_DATA` components contain no generated forecast values, and missing critical inputs block opportunity scoring.
- Do not add authentication, marketplace listings, buyer-demand volumes, transactions, admin CRUD, or fabricated lower-resolution analytics.
- Do not modify `data/raw/` in place. Derived inputs belong in `data/processed/`.
- Each sprint ends with a runnable application, focused tests, and a concise completion report.

---

## 1. Validated Repository Baseline

This plan reflects repository state at commit `a920b90` on 2026-09-03. Repository evidence overrides older planning assumptions.

### Module status

| Module | Current state | Evidence | Remaining work |
|---|---|---|---|
| M01 App Shell & Setup | Implemented | `app/setup/page.tsx`, `AppPreferencesContext.tsx`, `preferences.ts`, sidebar | Cross-page integration and final resilience checks |
| M02 Forecast Inference & Contract | Implemented, with a dual-path demand caveat | `artifact_registry.py`, `forecast_service.py`, forecast schemas/router | Make demand provenance and fallback state explicit |
| M03 Dashboard | Implemented | `app/page.tsx` calls `/forecast/outlook` for all commodities | Add final navigation and error-state regression coverage |
| M04 Forecasting & Opportunity | Implemented | `app/forecasting/page.tsx`, `opportunity.py` | Expose rice gap clearly and align demand display semantics |
| M05 Explainability | Partial | methodology schema/types and metadata exist | Add endpoint and “Why this result?” UI |
| M06 GIS Analytics | Not implemented | PSGC province mapping exists; no mapping route or GIS module | Build province-honest analytical map |
| M07 Curated Markets | Data/contracts only | market CSVs, ranking config, API/TS schemas | Build registry, ranking, API, map/list UI |
| M08 Chatbot | Baseline implemented | RAG retriever, prompt, router, and chat page | Resolve and inject structured analytics context |
| M09 Model Evidence | API implemented | `ForecastService.evidence()`, `/forecast/evidence`, evidence schema/tests | Build frontend evidence page |
| M10 UX Resilience | Partial | loading/error/unsupported states exist in core pages | Finish stale-data, mobile, low-bandwidth, and integration QA |

### Verified model matrix

| Commodity | Demand | Supply | Price | Opportunity consequence |
|---|---|---|---|---|
| Rice | `USABLE_PROXY`; BREAD category proxy. Optional FIES/XGBoost benchmark path can return quarterly MT estimates. | `CAUTION`; histogram gradient boosting | `PASS`; histogram gradient boosting | Available when all three component forecasts share a quarter; a physical MT gap is available only with the optional rice pipeline |
| Tomato | `USABLE_PROXY`; shared VEG category proxy | `CAUTION`; random forest | `CAUTION`; random forest | Available as a peer-relative score; no physical demand-supply subtraction |
| Red Onion | `USABLE_PROXY`; shared VEG category proxy | `INSUFFICIENT_DATA`; seasonal-naive comparison retained | `INSUFFICIENT_DATA`; no deployable artifact | Unavailable because critical supply and price inputs are missing |
| Banana | `USABLE_PROXY`; FRUIT category proxy | `PASS`; seasonal naive | `PASS`; random forest | Available as a peer-relative score; no physical demand-supply subtraction |

### Current API surface

| Endpoint | State | Consumer |
|---|---|---|
| `GET /forecast/catalog` | Implemented | setup, filters, future map/market views |
| `GET /forecast/outlook?commodity=&province=` | Implemented | dashboard and forecasting |
| `GET /forecast/evidence` | Implemented | planned model-evidence page |
| `GET /forecast/methodology` | Not implemented | planned explainability UI; frontend fetch helper already exists |
| `POST /rag/query` | Baseline implemented | chat page; analytics context is not yet injected |
| `/markets/*` | Not implemented | planned markets list/map |

---

## 2. Current Demand Retrieval and Inference Logic

The demand path must be understood before changing the forecast contract.

### Startup and artifact retrieval

1. `apps/api/app/main.py` creates one `ArtifactRegistry` during FastAPI lifespan startup.
2. `ArtifactRegistry.load()` validates schema version `3.2`, trusted paths, artifact identity, model presence, feature lists, metrics, and limitations.
3. Demand registration is:

   - Rice → `ml/artifacts/demand/rice.joblib`
   - Tomato → `ml/artifacts/demand/vegetable_shared.joblib`
   - Red Onion → the same `vegetable_shared.joblib` object
   - Banana → `ml/artifacts/demand/banana.joblib`

4. The registry normalizes each bundle into component metadata with verdict `USABLE_PROXY`.
5. The same startup attempts to load `DemandPredictionPipeline(data/processed)` for the optional rice FIES/XGBoost path.
6. A clean checkout contains only `data/processed/.gitkeep`, so the optional pipeline raises `DemandPipelineError` and the API intentionally starts with `demand_pipeline=None`.

### Default demand response path

For every commodity when the optional pipeline is absent—and always for tomato, red onion, and banana—`ForecastService._demand_component()` does not call the loaded joblib model at request time. It retrieves:

- observed quarterly indices from `quarterly_demand_pressure_index.csv`; and
- the next three prepared proxy values from `future_demand_pressure_3q.csv`.

The joblib bundle supplies validated identity, model/evidence metadata, metrics, verdict, and limitations. The served forecast values are precomputed snapshot values.

### Optional rice benchmark path

When all required files exist under `data/processed/`, `DemandPredictionPipeline.load()`:

1. loads the XGBoost feature manifest and Model B JSON once;
2. predicts annual household BREAD expenditure for the processed 2023 FIES/LFS table;
3. multiplies predictions by `SURVEY_WEIGHT` and aggregates to one CALABARZON annual estimate;
4. allocates that estimate to provinces using spatial benchmark shares;
5. allocates each province to four quarters using temporal benchmark shares; and
6. evaluates household and province-aggregate held-out predictions.

At request time, rice quarterly expenditure is converted to metric tons using the matching or fallback farmgate price:

```text
estimated_demand_mt = quarterly_expenditure_php / price_php_per_kg / 1,000
supply_gap_mt = estimated_demand_mt - predicted_supply_mt
```

Positive gap means estimated unmet demand; negative gap means estimated surplus. This physical gap must not be generalized to commodities whose demand output is an index.

### Demand-path risks to resolve

- The public response does not explicitly identify whether rice came from the committed prepared-proxy path or the optional FIES/XGBoost benchmark path.
- Rice changes unit from `index` to `MT` when the optional pipeline loads, while the same component contract remains in use.
- Demand joblib models are loaded for all commodities, but default request-time values come from prepared CSVs. UI and evidence copy must not imply live joblib inference.
- The optional processed inputs are not committed, so local/CI behavior differs from a deployment that has them.
- `data_as_of` is a date for the prepared path but a year string for benchmarked rice.
- A generic “demand-supply gap” is scientifically unsupported for tomato, red onion, and banana under the present artifacts.

---

## 3. Supply, Price, and Opportunity Logic to Preserve

### Supply

- `ForecastService._modeled_component()` reads each commodity's prepared supply feature table.
- Observed values come from non-null `target` rows.
- Up to three future quarterly rows are predicted with the loaded learned model or seasonal-naive history.
- Red onion remains `INSUFFICIENT_DATA`; its comparison artifact must not produce a forecast.

### Price

- Price uses the same modeled-component path with monthly prepared rows.
- Up to three future monthly values are returned.
- Red onion has no deployable price artifact and remains value-free.
- Quarterly consumers, such as opportunity and rice gap, average the matching monthly price points.

### Opportunity

- Opportunity is computed across all five CALABARZON provinces for one commodity.
- The earliest quarter shared by demand, supply, and price is selected.
- Demand, inverse supply/scarcity, and price are independently converted to province-relative percentile scores.
- Confidence uses `HIGH=100`, `MODERATE=60`, and `NONE=0`.
- Configured weights are demand `0.35`, scarcity `0.25`, price `0.20`, and confidence `0.10`; weights are renormalized over the included configured components.
- Classifications are `HIGH_OPPORTUNITY`, `UNDERSUPPLY_LEANING`, `BALANCED`, `OVERSUPPLY_LEANING`, and `SEVERE_OVERSUPPLY`.
- Any missing demand, supply, price, or confidence value returns `INSUFFICIENT_DATA` with no score or classification.
- The result is a peer-relative decision-support score, not learned ground truth and not a physical supply gap.

---

## 4. Sprint Roadmap

## Sprint 0 — Repository and Model Audit — COMPLETE

**Modules:** M02 foundation; reuse assessment for M01–M10

**Delivered:**

- [x] Artifact inventory and schema `3.2` validation
- [x] Four-commodity demand/supply/price verdict matrix
- [x] Province and frequency constraints
- [x] RAG source and market-data inventory
- [x] Architecture audit in `docs/architecture/sprint-0-audit.md`

**Exit evidence:** The artifact bundle and frozen contracts are committed and documented.

## Sprint 0.5 — Shared Contract Freeze — COMPLETE

**Modules:** M01, M02, M07, M08, M09

**Delivered:**

- [x] Forecast, market, RAG-context, and evidence Pydantic schemas
- [x] Matching TypeScript types and fixtures
- [x] Commodity, province, preference, and analytics-context utilities
- [x] `PASS`, `CAUTION`, `INSUFFICIENT_DATA`, and `USABLE_PROXY` vocabulary

**Exit evidence:** Backend contract tests and frontend fixture/type checks exist.

## Sprint 1 — Runtime Foundations — COMPLETE

**Modules:** M01, M02, M08 baseline, part of M10

**Delivered:**

- [x] Cached artifact registry and forecast service
- [x] Catalog and outlook endpoints
- [x] Setup flow, local preferences, shared application state, and navigation
- [x] RAG retrieval/query baseline and chat page
- [x] Explicit insufficient-data responses

**Known limitation:** The RAG baseline is document-only; it does not yet resolve analytics context.

## Sprint 2 — Dashboard, Forecasting, Demand Benchmark, and Opportunity — COMPLETE WITH HARDENING FOLLOW-UP

**Modules:** M03, M04, M09 backend, part of M10

**Delivered:**

- [x] CALABARZON dashboard using actual outlook API responses
- [x] Forecasting controls and demand/supply/price cards
- [x] Observed, forecast, proxy, verdict, confidence, source, frequency, and resolution displays
- [x] Configured peer-relative opportunity scoring
- [x] Optional rice FIES/XGBoost benchmark and MT supply-gap logic
- [x] Cached model-evidence extraction and `/forecast/evidence`

**Follow-up acceptance:** Sprint 3 must make demand provenance and the rice fallback mode explicit before GIS or chatbot reuse the values.

## Sprint 3 — Forecast Contract Hardening and Explainability

**Modules:** M02, M04, M05, part of M09 and M10

**Files:**

- Modify: `ml/forecasting/forecast_service.py`
- Modify: `apps/api/app/schemas/forecast.py`
- Modify: `apps/api/app/routers/forecast.py`
- Modify: `apps/web/src/types/forecast.ts`
- Modify: `apps/web/app/forecasting/page.tsx`
- Create: `apps/web/app/components/WhyThisResult.tsx`
- Test: `tests/test_forecast_service.py`, `tests/test_forecast_router.py`, `tests/test_forecast_evidence.py`
- Test: focused frontend component/helper tests under `apps/web/`

### Task 3.1 — Make demand provenance explicit

- [ ] Add contract fields that distinguish `prepared_proxy_snapshot` from `fies_xgboost_benchmark` without changing the `Estimated Demand Proxy` label.
- [ ] Normalize `data_as_of` to one documented representation.
- [ ] Test clean-checkout fallback, optional-pipeline success, rice unit behavior, and non-rice prepared-snapshot behavior.
- [ ] Ensure evidence describes the model used to create each output rather than implying request-time inference where none occurs.

### Task 3.2 — Complete methodology and explanation

- [ ] Implement `GET /forecast/methodology` from the cached methodology and opportunity configuration.
- [ ] Add “Why this result?” for demand, supply, price, rice gap, and opportunity.
- [ ] Show model/verdict, leading available factors, confidence reason, source, frequency, resolution, data coverage, and limitations.
- [ ] State explicitly that proxy estimates and opportunity associations are not causal findings.
- [ ] Do not invent confidence intervals; omit them or label them unavailable when artifacts do not provide them.

### Task 3.3 — Preserve analytical invariants

- [ ] Keep red onion supply/price value-free and opportunity unavailable.
- [ ] Keep physical `supply_gap_mt` limited to benchmarked rice.
- [ ] Keep peer-relative opportunity scoring unchanged unless configuration and tests are updated together.
- [ ] Prevent stale component values after a failed or changed request.

**Verification:**

```powershell
pytest tests/test_demand_pipeline.py tests/test_forecast_service.py tests/test_forecast_router.py tests/test_forecast_evidence.py tests/test_opportunity.py
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
```

**Exit flow:** `Dashboard → Forecasting → Why this result?`

## Sprint 4 — GIS Analytics and Curated Markets

**Modules:** M06, M07, part of M10

**Files:**

- Create: `apps/web/app/mapping/page.tsx`
- Create: `apps/web/src/gis-map/` focused map/data adapters
- Create: `markets/registry.py`, `markets/ranking.py`
- Create: `apps/api/app/routers/markets.py`
- Create: `apps/web/app/markets/page.tsx`
- Reuse: `ml/artifacts/market_coordinates/*.csv`, `market_recommendation_config.json`
- Test: new market registry/ranking/API tests and frontend map/market helper tests

### Task 4.1 — Build a province-honest analytics map

- [ ] Load or vendor the required CALABARZON boundary assets through the existing frontend pattern.
- [ ] Add demand, supply, price, opportunity, and rice-gap layers only when the selected response supports them.
- [ ] Label municipality drill-down with the source province and true province resolution.
- [ ] Show loading, API error, unsupported layer, and insufficient-data states without retaining stale map values.

### Task 4.2 — Build the curated market registry and ranking

- [ ] Validate stable market IDs, province/municipality fields, coordinates, coordinate confidence, and public source/context fields.
- [ ] Preserve missing or approximate coordinates instead of fabricating exact points.
- [ ] Rank using configured proximity, market-size proxy, data reliability, and supported analytics inputs.
- [ ] Explain that straight-line distance is not travel time and market size is not buyer demand.
- [ ] Return a component breakdown and “Why recommended?” explanation.

### Task 4.3 — Integrate market list and map

- [ ] Add commodity/province filters synchronized with shared application state.
- [ ] Provide list/map selection, compare, “View on Map,” and “Ask AgriWise” link preparation.
- [ ] Do not add listings, inquiries, transactions, moderation, or buyer-demand quantities.

**Verification:**

```powershell
pytest tests/test_forecast_service.py tests/test_opportunity.py tests/test_markets_registry.py tests/test_market_ranking.py tests/test_markets_router.py
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
```

**Exit flow:** `Forecasting ↔ Mapping → Markets → Why recommended?`

## Sprint 5 — Model Evidence UI and Contextual Ask AgriWise

**Modules:** M08, M09, part of M10

**Files:**

- Create: `apps/web/app/model-evidence/page.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/api/app/routers/rag.py`
- Modify: `rag/prompt.py`
- Modify: `apps/web/app/chat/page.tsx`
- Modify: Forecasting, mapping, markets, and explanation entry points
- Test: `tests/test_prompt.py`, `tests/test_rag_router.py`, `tests/test_forecast_evidence.py`, and frontend analytics-context/chat tests

### Task 5.1 — Present model evidence

- [ ] Consume `/forecast/evidence` and render all four commodities by demand, supply, and price.
- [ ] Show target, model, metrics, verdict, reason, frequency, province resolution, source, artifact version, and limitations.
- [ ] Keep missing models and metrics visibly unavailable.
- [ ] Show tomato and red onion demand as the same shared vegetable proxy evidence.

### Task 5.2 — Resolve structured analytics context

- [ ] Resolve commodity, province, selected view, and optional market ID server-side from trusted service data.
- [ ] Add current component values, verdicts, units, periods, sources, limitations, opportunity breakdown, and selected market metadata.
- [ ] Never trust client-supplied numeric analytics as authoritative.
- [ ] Keep context size bounded and deterministic.

### Task 5.3 — Ground chatbot explanations

- [ ] Inject structured analytics context separately from retrieved document context.
- [ ] Require the prompt to distinguish observed values, model predictions, prepared proxies, and benchmarked estimates.
- [ ] Require an explicit “not observed consumption” disclosure for demand.
- [ ] Refuse to reconstruct missing red onion forecasts or unavailable opportunity scores.
- [ ] Preserve source citations and agricultural safety escalation language.

**Verification:**

```powershell
pytest tests/test_prompt.py tests/test_rag_router.py tests/test_retriever.py tests/test_forecast_evidence.py
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
```

**Exit flow:** `Forecasting / Explanation / Mapping / Markets → Ask AgriWise`

## Sprint 6 — Integrated QA and Demo Release

**Modules:** M01–M10, led by M10

### Task 6.1 — Analytical regression

- [ ] Verify every commodity/province combination for demand, supply, price, opportunity, and warnings.
- [ ] Run both rice demand modes: clean-checkout fallback and optional benchmark pipeline.
- [ ] Confirm supply and price frequency, province resolution, and red onion insufficient-data behavior.
- [ ] Confirm opportunity uses a shared quarter, configured weights, and no incompatible-unit subtraction.
- [ ] Confirm cached registry/service behavior and deterministic repeated responses.

### Task 6.2 — End-to-end user journey

- [ ] Verify `Landing → Setup → Dashboard → Forecasting` without an account.
- [ ] Verify selection consistency through Forecasting, Mapping, Markets, Explanation, and Chat.
- [ ] Verify all loading, error, empty, unsupported-resolution, and insufficient-data states.
- [ ] Verify no previous commodity values remain after a failed request.
- [ ] Verify keyboard navigation, readable mobile layouts, and low-bandwidth behavior.

### Task 6.3 — Release evidence

- [ ] Run the complete Python and frontend suites in the documented environments.
- [ ] Record any unavailable external prerequisites, including Groq credentials and optional processed FIES files.
- [ ] Update `README.md` status so it matches the completed routes and modules.
- [ ] Prepare a demo matrix covering one fully supported commodity, one caution case, and red onion insufficient data.

**Verification:**

```powershell
pytest
ruff check apps/api ml rag markets tests
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
```

**Exit flow:** `FORECAST → MAP → EXPLAIN → RECOMMEND → ASK AGRIWISE`

---

## 5. Sprint Execution Rules

For every implementation pull request:

1. State the sprint and module IDs.
2. List reused and changed files.
3. Write or update focused tests before changing behavior.
4. Preserve the shared contract unless the pull request explicitly migrates both backend and frontend consumers.
5. Report commands run and their actual outcomes.
6. Report the newly working user-flow path and known limitations.
7. Keep one logical change per pull request and avoid concurrent edits to the same page.

Recommended ownership boundaries for three developers:

| Track | Primary ownership |
|---|---|
| Forecast | Demand, supply, price, opportunity, forecast API, explainability |
| Experience | Setup, dashboard, shared state, GIS, UX resilience |
| Integration | Markets, RAG/chat, model-evidence UI, release integration |

Cross-track contract changes require review from every affected consumer before merge.

---

## 6. Definition of Done

The MVP is complete when an anonymous user can:

1. save municipality and crop preferences locally;
2. view actual CALABARZON outlook responses for all four commodities;
3. distinguish observed supply/price values, predictions, prepared demand proxies, and optional benchmarked rice estimates;
4. see verdict, confidence, source, frequency, province resolution, data-as-of, and model evidence;
5. understand why a result or opportunity classification was shown;
6. view supported analytics on a province-honest GIS map;
7. discover and compare curated public markets with transparent ranking limitations;
8. ask AgriWise to explain the trusted current analytics context with citations;
9. receive explicit insufficient-data responses instead of fabricated red onion supply, price, gap, or opportunity values; and
10. complete the workflow `FORECAST → MAP → EXPLAIN → RECOMMEND → ASK AGRIWISE` in a tested production build.

## 7. Completion Report Template

```text
Sprint N

Modules completed:
- M0X — name

Important files changed:
- path/to/file

Verification:
- command — PASS/FAIL and concise reason

Working user flow:
- start → destination

Known limitations:
- evidence-backed limitation or “None”
```

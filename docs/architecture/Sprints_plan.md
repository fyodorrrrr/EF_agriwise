# AgriWise MVP Completion Sprint Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the AgriWise hackathon MVP from the repository's current working baseline while keeping demand, supply, price, and opportunity outputs scientifically honest and consistent across the dashboard, forecasting, mapping, markets, evidence, and chatbot experiences.

**Architecture:** FastAPI loads the versioned forecasting snapshot once, exposes province-resolution analytics through typed contracts, and supplies those contracts to a Next.js application. Demand has a committed proxy path for all commodities and an optional FIES/XGBoost benchmark path for rice; supply and price use their validated component artifacts; opportunity combines normalized peer-relative inputs without subtracting incompatible units.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pandas, NumPy, scikit-learn/joblib, optional XGBoost, pytest, Next.js 16 App Router, React, TypeScript, Tailwind CSS 4, Vitest.

**Specs and evidence:** `ml/artifacts/README.md` (forecast-service artifact registry contract and verdict tiers), `ml/demand/README.md` (isolated FIES/LFS quarterly demand pipeline), the committed artifact bundles under `ml/artifacts/{demand,supply,price}/`, and the checked-in contracts in `apps/api/app/schemas/forecast.py` and `apps/web/src/types/`.

> **Re-baseline note (2026-09-08, commit `f07633a`).** Section 1 was rewritten to match this repository. The earlier baseline (commit `a920b90`) and the files it cites — `docs/architecture/sprint-0-audit.md`, `fies-demand-benchmark-pipeline.md`, `CODEBASE_CONTEXT.md`, `ml/artifacts/reports/unified_deployment_summary.csv` — describe a different codebase and are **not present here**. This repo is a leaner reimplementation currently at the end of Sprint 1. Sprint 2 has been split into **2a (forecast-value + evidence backend)**, **2b (opportunity engine)**, and **2c (dashboard + forecasting UI)**.

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

This plan reflects repository state at commit `f07633a` on 2026-09-08. Repository evidence overrides older planning assumptions. Every "Implemented" claim carried over from the `a920b90` baseline is superseded by the table below.

### Module status

| Module | Current state | Evidence | Remaining work |
|---|---|---|---|
| M01 App Shell & Setup | Implemented | `apps/web/src/app/setup/page.tsx`, `AppPreferencesContext` + `preferences.tsx` (with tests), sidebar/navigation, `ComingSoon` shell for unbuilt routes | Wire real pages into shared state as they land |
| M02 Forecast Inference & Contract | **Partial — registry + contract only** | `artifact_registry.py` (loads bundle metadata only; comment: "no schema-version or feature-list validation yet"), `forecast_service.py` (returns each artifact's own verdict/metrics/limitations; comment: forward-looking value generation is "not-yet-designed"), `apps/api/app/schemas/forecast.py`, `GET /forecast/{catalog,outlook}` | Generate forecast values (Sprint 2a); harden registry to schema `3.2`; add evidence extraction |
| M03 Dashboard | **Not implemented** | `apps/web/src/app/page.tsx` is a `ComingSoon` stub | Sprint 2c |
| M04 Forecasting & Opportunity | **Not implemented** | `apps/web/src/app/forecasting/page.tsx` is a `ComingSoon` stub; `forecast_service.outlook()` hardcodes `_insufficient_data_opportunity()` — no opportunity engine exists | Opportunity engine (Sprint 2b); forecasting UI (Sprint 2c) |
| M05 Explainability | Not implemented | no `/forecast/methodology`, no "Why this result?" component, no methodology schema | Sprint 3 |
| M06 GIS Analytics | Not implemented | `mapping/page.tsx` stub | Sprint 4 |
| M07 Curated Markets | Data only | `ml/artifacts/market_coordinates/*.csv` (currently untracked), `market_recommendation_config.json`; no registry, ranking, API, schema, or UI | Sprint 4 |
| M08 Chatbot | Baseline implemented | `rag/` pipeline, `POST /rag/query`, `chat/page.tsx` (with test) | Inject structured analytics context — Sprint 5 |
| M09 Model Evidence | **Not implemented** | no `/forecast/evidence`, no `ForecastService.evidence()`, no evidence schema or tests | Backend in Sprint 2a; frontend in Sprint 5 |
| M10 UX Resilience | Partial | loading/error/unsupported states in `setup` and `chat`; every other route is `ComingSoon` | Finish per real page as it lands |

Also absent vs. the old baseline: `CODEBASE_CONTEXT.md`, the `docs/architecture/sprint-0-audit.md` / `fies-demand-benchmark-pipeline.md` specs, `ml/artifacts/reports/`, `apps/web/src/types/` may be thinner than assumed, and there are no `pytest` suites under a top-level `tests/` — backend tests live in `apps/api/tests/`, `rag/tests/`, and `ml/demand/tests/`.

### Two artifact stores (do not conflate)

| | `ml/artifacts/` | `ml/demand/` |
|---|---|---|
| Format | `joblib`-pickled dict bundles per `{component}/{commodity}.joblib`, schema `3.2` | native XGBoost JSON boosters + feature/parameter manifests |
| Consumed by | `ArtifactRegistry` → `ForecastService` → `/forecast/outlook` | `ml/demand/pipeline/` (Denton benchmarking + spatial reconciliation); **not wired into the API** |
| Contents | demand/supply/price bundles for all 4 commodities (committed) | FIES/LFS household `BREAD`/`VEG` expenditure "Model B" |
| Runtime inputs it needs | supply/price bundles carry `model` + `history_tail` + `seasonal_period` and are self-contained; demand bundles are **cross-sectional 2023 estimators with no time series** | `data/processed/demand/` LFS feature rows + benchmark CSVs — **none committed**; `run_pipeline.py` "intentionally fails at the inference boundary" in this checkout |

### Verified model matrix (bundle verdicts at `f07633a`)

| Commodity | Demand | Supply | Price | Opportunity consequence |
|---|---|---|---|---|
| Rice | `USABLE_PROXY`; `BREAD` category, cross-sectional 2023 FIES estimator (no quarterly series yet) | `CAUTION`; hist gradient boosting, 40 quarterly history points | `PASS`; hist gradient boosting, 120 monthly points | Peer-relative score once 2a produces a demand series and 2b lands; no physical MT gap (rice FIES benchmark not wired) |
| Tomato | `INDICATIVE_PROXY`; shared `VEG` estimator | `CAUTION`; random forest, seasonal period 4 | `CAUTION`; random forest, seasonal period 12 | Peer-relative score after 2a + 2b; no physical demand−supply subtraction |
| Red Onion | `INDICATIVE_PROXY`; same shared `VEG` estimator | `INSUFFICIENT_DATA`; seasonal-naive comparison, `model=None` | no bundle → `INSUFFICIENT_DATA` | Unavailable — critical supply and price inputs missing |
| Banana | `INDICATIVE_PROXY`; `FRUIT` category estimator | `CAUTION`; seasonal-naive, `model=None` | `PASS`; random forest, seasonal period 12 | Peer-relative score after 2a + 2b; no physical demand−supply subtraction |

`INDICATIVE_PROXY` is a real verdict in `apps/api/app/schemas/forecast.py`; the shared `VEG` model backs both Tomato and Red Onion demand (two files, one estimator, keyed on the `commodity` field).

### Current API surface

| Endpoint | State | Consumer |
|---|---|---|
| `GET /forecast/catalog` | Implemented | setup, filters, future map/market views |
| `GET /forecast/outlook?commodity=&province=` | Implemented — **returns verdict/metrics/limitations only, no `values`** | dashboard and forecasting (once built) |
| `GET /forecast/evidence` | **Not implemented** | Sprint 2a → model-evidence page |
| `GET /forecast/methodology` | Not implemented | Sprint 3 explainability UI |
| `POST /rag/query` | Baseline implemented | chat page; analytics context not injected |
| `/markets/*` | Not implemented | Sprint 4 markets list/map |

---

## 2. Current Demand Retrieval and Inference Logic

### What exists today (commit `f07633a`)

1. `apps/api/app/main.py` builds one `ArtifactRegistry` during FastAPI lifespan startup from `settings.forecast_artifacts_dir` (`ml/artifacts`).
2. `ArtifactRegistry.load()` does **not** validate schema version, trusted paths, feature lists, or model presence yet. It `joblib.load`s each `{component}/{commodity}.joblib`, reads `commodity`/`model_id`/`verdict`/`metrics`/`limitations`, and on any exception logs a warning and treats the bundle as absent. A missing/empty directory yields an empty registry, not an error.
3. Demand bundles registered: `rice.joblib` (`BREAD`, `USABLE_PROXY`), `tomato.joblib` and `red_onion.joblib` (both the shared `VEG` estimator, `INDICATIVE_PROXY`), `banana.joblib` (`FRUIT`, `INDICATIVE_PROXY`).
4. `ForecastService.outlook()` returns, per component, only the bundle's own `verdict`, `metrics`, and `limitations`. **No `values`, `unit`, `frequency`, `confidence`, `source`, or `data_as_of`** — the code comment states forward-looking value generation is "a separate, not-yet-designed piece of work".
5. There is no `DemandPredictionPipeline` wired into startup, no `data/processed/` demand inputs, and no rice FIES/XGBoost benchmark path in the API.

### Why demand values are the hard part

The demand `.joblib` bundles are **cross-sectional 2023 FIES household-expenditure estimators** (features `FSIZE`, `URB`, `TOINC`, …), explicitly limited as "not an observed quarterly demand forecast." They carry no `history_tail` and no time series. Producing a province×quarter **Estimated Demand Proxy** series therefore requires one of:

- **Option A — precomputed series (recommended for Sprint 2a):** run the estimator + FIES/LFS table + spatial/temporal (Denton) allocation **offline**, commit the resulting `province × quarter` proxy series as a CSV under `ml/artifacts/demand/` (or `data/processed/demand/`), and have `ForecastService` read it at request time. Fast, deterministic, no XGBoost at runtime.
- **Option B — wire `ml/demand/`:** commit `data/processed/demand/` LFS feature rows + benchmark CSVs and call `ml/demand/pipeline/run_pipeline.py` / `inference.py`. Heavier: adds `xgboost` as an API runtime dependency (not currently installed in `apps/api/.venv`) and a Model-B feature contract that the repo's regional LFS table "intentionally fails" to satisfy.

Sprint 2a picks Option A unless a decision record says otherwise.

### Contract fields already reserved

`apps/api/app/schemas/forecast.py` documents deferred work: a `demand_label` field enforcing "Estimated Demand Proxy" wording, `data_as_of` format reconciliation, and the `/forecast/evidence` + `/forecast/methodology` shapes. `Verdict` already includes `USABLE_PROXY` and `INDICATIVE_PROXY`.

### Demand risks to resolve

- The rice FIES/XGBoost benchmark path and its physical `supply_gap_mt` do not exist here. When/if added, they must be gated and clearly distinguished from the index/proxy path (Sprint 3, Task 3.1).
- A generic "demand−supply gap" is scientifically unsupported for all four commodities under the committed artifacts — demand output is a proxy index, not physical volume.
- Evidence/UI copy must not imply request-time joblib inference; the served demand values will be precomputed snapshot values.

---

## 3. Supply, Price, and Opportunity — Target Logic

None of the logic in this section is implemented yet. It is the design Sprint 2a (supply/price) and Sprint 2b (opportunity) must build. The supply/price target is achievable now because each `ml/artifacts/{supply,price}/{commodity}.joblib` bundle is self-contained.

### Supply

- Each supply bundle carries `model` (a fitted sklearn `Pipeline`, or `None`), `strategy`, `features`, `seasonal_period` (4), and `history_tail` (~40 quarterly points). No external feature table is needed.
- A shared `_modeled_component()` returns the observed tail plus up to three predicted future quarters — from the learned model when present (`rice`: hist gradient boosting; `tomato`: random forest), otherwise seasonal-naive from `history_tail` (`banana`).
- Red onion supply is `INSUFFICIENT_DATA` with `model=None`; it must stay value-free.

### Price

- Same modeled-component path with monthly bundles: `seasonal_period` 12, `history_tail` ~120 months. `rice` hist gradient boosting, `tomato`/`banana` random forest.
- Up to three future monthly values are returned.
- Red onion has **no price bundle at all** — it stays `INSUFFICIENT_DATA` and value-free.
- Quarterly consumers (opportunity, any future rice gap) average the matching monthly price points.

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

- [x] Artifact inventory — bundles committed under `ml/artifacts/{demand,supply,price}/`; contract documented in `ml/artifacts/README.md`
- [x] Four-commodity demand/supply/price verdict matrix (see Section 1)
- [x] Province and frequency constraints (see Global Constraints)
- [x] RAG source and market-data inventory (`data/raw/*.pdf`, `ml/artifacts/market_coordinates/`)
- [ ] Standalone `docs/architecture/sprint-0-audit.md` — not present; audit content folded into Section 1 of this file
- [ ] `schema_version` `3.2` is *stamped* on bundles but *not validated* at load — deferred to Sprint 2a

**Exit evidence:** The artifact bundles and forecast/RAG contracts are committed; `ml/artifacts/README.md` and `ml/demand/README.md` document them.

## Sprint 0.5 — Shared Contract Freeze — PARTIAL

**Modules:** M01, M02, M08

**Delivered:**

- [x] Forecast Pydantic schemas (`apps/api/app/schemas/forecast.py`) and RAG schemas (`rag.py`)
- [x] `PASS`, `CAUTION`, `INSUFFICIENT_DATA`, `USABLE_PROXY`, `INDICATIVE_PROXY` verdict vocabulary
- [x] Commodity / province / preference utilities (`ml/forecasting/domain.py`, `apps/web/src/lib/`)
- [ ] Market and evidence Pydantic schemas — not created (Sprint 2a evidence, Sprint 4 market)
- [ ] Analytics-context schema — not created (Sprint 5)

**Exit evidence:** `apps/api/tests/test_forecast_service.py`, `test_rag_schemas.py`; frontend `*.test.ts(x)` under `apps/web/src/lib/`.

## Sprint 1 — Runtime Foundations — COMPLETE

**Modules:** M01, M02, M08 baseline, part of M10

**Delivered:**

- [x] Cached artifact registry and forecast service
- [x] Catalog and outlook endpoints
- [x] Setup flow, local preferences, shared application state, and navigation
- [x] RAG retrieval/query baseline and chat page
- [x] Explicit insufficient-data responses

**Known limitations:**

- The RAG baseline is document-only; it does not yet resolve analytics context.
- `/forecast/outlook` returns verdict/metrics/limitations only. Forecast-value generation was explicitly deferred (see `forecast_service.py`).
- `ArtifactRegistry` does no schema/feature validation; a broken bundle is silently skipped.
- Opportunity is hardcoded to `INSUFFICIENT_DATA`.

---

## Sprint 2 — split into 2a / 2b / 2c

The original single Sprint 2 assumed M02/M03/M04 were already "Implemented." Against commit `f07633a` they are registry-and-contract only (2a), nonexistent (2b), and stubs (2c). The three sub-sprints are ordered: **2a → 2b → 2c**. The optional rice FIES/XGBoost benchmark and physical MT `supply_gap_mt` are **removed from Sprint 2** and folded into Sprint 3 (Task 3.1), since they need uncommitted `data/processed/` inputs and an `xgboost` runtime dependency.

### Recommended build order

**Step 0 — fix the silent demand-bundle load failure (do this first).** `ml/artifacts/demand/tomato.joblib` and `red_onion.joblib` pickle an XGBoost estimator. `xgboost>=3.4.1` is declared in `pyproject.toml` and pinned in `uv.lock`, but a drifted `.venv` (no `uv sync`) makes the bundles fail to unpickle at startup; `ArtifactRegistry._load_bundle` swallows the error, so Tomato and Red Onion demand silently degrade to `INSUFFICIENT_DATA` instead of `INDICATIVE_PROXY`.

- [x] Run `uv sync` — restores `xgboost` from the lockfile (no `pyproject.toml`/`uv.lock` change needed).
- [x] Regression test `test_all_committed_artifact_bundles_load` asserts **all 11 committed bundles register** (Rice/Tomato/Red Onion/Banana demand + supply; Rice/Tomato/Banana price).
- [ ] Longer-term cleanup (Task 2a.1 / retraining): re-dump the shared `VEG` demand bundle without a pickled XGBoost object so the forecast-service store stays lightweight per `ml/artifacts/README.md` and needs no `xgboost` at runtime.

**Then, within Sprint 2a:**

| Order | Work | Notes |
|---|---|---|
| 1 | **Supply + price values** — `_modeled_component()`, populate `values`/`unit`/`frequency`/`confidence`/`source`/`data_as_of` (Task 2a.2) | Zero blockers; bundles are self-contained (`model` + `history_tail` + `seasonal_period`). Immediately returns real numbers for rice/tomato/banana. |
| 2 | **`/forecast/evidence`** endpoint (Task 2a.4) | Small, independent — pure metadata read; can even precede #1. |
| 3 | **Registry hardening to schema `3.2`** — rest of Task 2a.1 | Fold in with #1; motivated by the Step 0 bug. |
| 4 | **Demand proxy series** (Task 2a.3) | Do last in 2a — needs the Option A vs B decision (Section 2) and the FIES/LFS table to generate the offline series. Demand honestly stays verdict-only until it lands. |

**Then 2b (opportunity engine)** — mechanical once 2a gives it values sharing a quarter — **then 2c (dashboard + forecasting UI)**.

**Do not start with 2c.** The pages are only as good as the API behind them; building them against verdict-only responses guarantees rework.

## Sprint 2a — Forecast-Value + Evidence Backend

**Modules:** M02, M09 backend

**Goal:** `/forecast/outlook` returns real `values` for every component that has a usable artifact, and a new `/forecast/evidence` exposes model provenance. Demand serves a committed precomputed proxy series (Section 2, Option A). No frontend work.

**Files:**

- Modify: `ml/forecasting/artifact_registry.py` (schema `3.2` validation: `schema_version`, `commodity` identity, `model`/`strategy` presence for modeled components, `features`, `history_tail`, `metrics`, `limitations`)
- Modify: `ml/forecasting/forecast_service.py` (add `_modeled_component()` for supply/price, `_demand_component()` reading the committed proxy series, `evidence()`)
- Modify: `apps/api/app/schemas/forecast.py` (populate `values`/`unit`/`frequency`/`confidence`/`source`/`data_as_of`; add `demand_label`; add `EvidenceResponse`)
- Modify: `apps/api/app/routers/forecast.py` (add `GET /forecast/evidence`)
- Create: `ml/artifacts/demand/proxy_series.csv` (or `data/processed/demand/`) — province × quarter Estimated Demand Proxy, produced offline; document the generator in `ml/artifacts/README.md`
- Test: `apps/api/tests/test_artifact_registry.py`, `test_forecast_service.py`, `test_forecast_router.py`, new `test_forecast_evidence.py`

### Task 2a.1 — Harden the artifact registry to schema 3.2

- [ ] Validate `schema_version == "3.2"`, `commodity` matches the filename slug and `COMMODITIES`, and required keys per `kind`.
- [ ] Fail loud in a dev/strict mode; keep prod behavior (skip + warn) but surface skipped bundles in a `registry.diagnostics` list.
- [ ] Assert the shared `VEG` estimator is loaded once and keyed to both Tomato and Red Onion.

### Task 2a.2 — Generate supply and price forecast values

- [ ] `_modeled_component()` returns observed `history_tail` + up to 3 future periods via the fitted `model`, else seasonal-naive via `seasonal_period`.
- [ ] Populate `unit`, `frequency` (`quarterly` supply / `monthly` price), `source`, `data_as_of`, and `metrics`-derived `confidence` (`HIGH`/`MODERATE`/`NONE`).
- [ ] Keep Red Onion supply and price value-free (`INSUFFICIENT_DATA`).
- [ ] Prevent stale values across requests — recompute or cache per `(commodity, province)` deterministically.

### Task 2a.3 — Serve the demand proxy series

- [ ] Commit the offline-generated province × quarter proxy series; `_demand_component()` reads it, never calls the joblib estimator at request time.
- [ ] Label every demand response **Estimated Demand Proxy**; carry the bundle `verdict` (`USABLE_PROXY` rice / `INDICATIVE_PROXY` others) and `limitations`.
- [ ] `data_as_of` is one documented representation (the series' last observed quarter).

### Task 2a.4 — `GET /forecast/evidence`

- [ ] `ForecastService.evidence()` returns, per commodity × component: target, model/`selected_model`, `metrics`, verdict + reason, frequency, province resolution, source, `schema_version`, `limitations`.
- [ ] Missing models/metrics render as explicitly unavailable, not zero.
- [ ] Tomato and Red Onion demand show the same shared `VEG` evidence.

**Verification:**

```powershell
cd apps/api
uv run pytest tests/test_artifact_registry.py tests/test_forecast_service.py tests/test_forecast_router.py tests/test_forecast_evidence.py
uv run ruff check app ../../ml
```

**Exit evidence:** `curl /forecast/outlook?commodity=Rice&province=Laguna` returns demand/supply/price `values`; `curl /forecast/evidence` returns the full 4×3 matrix; Red Onion supply/price stay value-free.

## Sprint 2b — Opportunity Engine

**Modules:** M04 backend

**Goal:** replace `_insufficient_data_opportunity()` with the configured peer-relative scorer from Section 3. Depends on 2a (needs demand/supply/price values sharing a quarter).

**Files:**

- Create: `ml/forecasting/opportunity.py`, `ml/forecasting/opportunity_config.json` (weights: demand `0.35`, scarcity `0.25`, price `0.20`, confidence `0.10`)
- Modify: `ml/forecasting/forecast_service.py` (call the scorer in `outlook()`)
- Modify: `apps/api/app/schemas/forecast.py` (`OpportunityComponent`: `score`, `classification`, `shared_quarter`, per-component breakdown)
- Test: new `apps/api/tests/test_opportunity.py`

### Task 2b.1 — Peer-relative scoring

- [ ] Compute across all five provinces for one commodity; select the earliest quarter shared by demand, supply, and price.
- [ ] Convert demand, inverse-supply (scarcity), and price to province-relative percentile scores; confidence `HIGH=100 / MODERATE=60 / NONE=0`.
- [ ] Renormalize configured weights over the components actually present.
- [ ] Classifications: `HIGH_OPPORTUNITY`, `UNDERSUPPLY_LEANING`, `BALANCED`, `OVERSUPPLY_LEANING`, `SEVERE_OVERSUPPLY`.

### Task 2b.2 — Fail closed

- [ ] Any missing demand / supply / price / confidence → `INSUFFICIENT_DATA`, no score, no classification (Red Onion always).
- [ ] Return the component breakdown for the future "Why this result?" UI.
- [ ] Document that this is a peer-relative decision-support score — not ground truth, not a physical supply gap.

**Verification:**

```powershell
cd apps/api
uv run pytest tests/test_opportunity.py tests/test_forecast_service.py tests/test_forecast_router.py
```

**Exit evidence:** `/forecast/outlook` returns an opportunity `score` + `classification` for Rice/Tomato/Banana on a shared quarter; Red Onion returns `INSUFFICIENT_DATA`.

## Sprint 2c — Dashboard + Forecasting UI

**Modules:** M03, M04 frontend, part of M10

**Goal:** replace the `page.tsx` and `forecasting/page.tsx` stubs with real pages driven by the 2a/2b API.

**Files:**

- Modify: `apps/web/src/app/page.tsx` (CALABARZON dashboard)
- Modify: `apps/web/src/app/forecasting/page.tsx` (controls + component cards)
- Modify/Create: `apps/web/src/types/forecast.ts`, `apps/web/src/lib/forecast.ts` (fetch helpers, already partly present), component tests
- Test: `apps/web/src/app/**/*.test.tsx`, `apps/web/src/lib/forecast.test.ts`

### Task 2c.1 — CALABARZON dashboard

- [ ] Call `/forecast/outlook` for all four commodities at the selected province from shared preferences.
- [ ] Show verdict, confidence, latest value, and trend per component; link through to Forecasting.
- [ ] Loading / API-error / insufficient-data states; no stale values after a failed refetch.

### Task 2c.2 — Forecasting page

- [ ] Commodity + province controls synced with `AppPreferences`.
- [ ] Demand / supply / price cards: observed vs. forecast values, **Estimated Demand Proxy** label, verdict, confidence, source, frequency, and the province-resolution note.
- [ ] Opportunity card: score, classification, shared quarter, component breakdown; `INSUFFICIENT_DATA` rendered honestly.
- [ ] Never present a province forecast as municipality-level.

**Verification:**

```powershell
cd apps/web
npm run test
npm run lint
npm run typecheck
npm run build
```

**Exit flow:** `Landing → Setup → Dashboard → Forecasting`

**Follow-up acceptance:** Sprint 3 must make demand provenance and any future rice benchmark mode explicit before GIS or chatbot reuse the values.

## Sprint 3 — Forecast Contract Hardening, Optional Rice Benchmark, and Explainability

**Modules:** M02, M04, M05, part of M09 and M10

**Absorbed from the old Sprint 2:** the optional rice FIES/XGBoost benchmark path and physical `supply_gap_mt` (Task 3.1). This requires committing `data/processed/demand/` inputs and adding `xgboost` to the API runtime, or vendoring `ml/demand/pipeline/` behind a feature flag — a deliberate, isolated decision, not a value-generation prerequisite for Sprints 2a–2c.

**Files:**

- Modify: `ml/forecasting/forecast_service.py`
- Modify: `apps/api/app/schemas/forecast.py`
- Modify: `apps/api/app/routers/forecast.py`
- Modify: `apps/web/src/types/forecast.ts`
- Modify: `apps/web/src/app/forecasting/page.tsx`
- Create: `apps/web/src/app/components/WhyThisResult.tsx`
- Test (under `apps/api/tests/`): `test_forecast_service.py`, `test_forecast_router.py`, `test_forecast_evidence.py`, `test_opportunity.py`
- Test: focused frontend component/helper tests under `apps/web/`

### Task 3.1 — Optional rice benchmark + demand provenance

- [ ] Decide and record: commit `data/processed/demand/` inputs + add `xgboost`, or defer the benchmark entirely.
- [ ] If built: load the pipeline only when inputs exist; API starts with `demand_pipeline=None` otherwise.
- [ ] Add contract fields that distinguish `prepared_proxy_snapshot` from `fies_xgboost_benchmark` without changing the `Estimated Demand Proxy` label.
- [ ] Keep the physical `supply_gap_mt` limited to benchmarked rice; never generalize it to the proxy-index commodities.
- [ ] Normalize `data_as_of` to one documented representation across both paths.
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
cd apps/api; uv run pytest tests/test_forecast_service.py tests/test_forecast_router.py tests/test_forecast_evidence.py tests/test_opportunity.py; cd ../..
# if the optional benchmark landed: cd ml/demand; uv run pytest tests; cd ../..
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

- Create: `apps/web/src/app/mapping/page.tsx`
- Create: `apps/web/src/gis-map/` focused map/data adapters
- Create: `markets/registry.py`, `markets/ranking.py`
- Create: `apps/api/app/routers/markets.py`
- Create: `apps/web/src/app/markets/page.tsx`
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
cd apps/api; uv run pytest tests/test_forecast_service.py tests/test_opportunity.py tests/test_markets_registry.py tests/test_market_ranking.py tests/test_markets_router.py; cd ../..
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

- Create: `apps/web/src/app/model-evidence/page.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/api/app/routers/rag.py`
- Modify: `rag/prompt.py`
- Modify: `apps/web/src/app/chat/page.tsx`
- Modify: Forecasting, mapping, markets, and explanation entry points
- Test: `rag/tests/test_prompt.py`, `apps/api/tests/test_rag_router.py`, `apps/api/tests/test_forecast_evidence.py`, and frontend analytics-context/chat tests

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
cd rag; uv run pytest tests/test_prompt.py tests/test_retriever.py; cd ..
cd apps/api; uv run pytest tests/test_rag_router.py tests/test_forecast_evidence.py; cd ../..
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
cd apps/api; uv run pytest; cd ../..
cd rag; uv run pytest; cd ..
cd ml/demand; uv run pytest; cd ../..
uv run ruff check apps/api/app ml rag markets
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

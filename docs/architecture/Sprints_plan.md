# AgriWise MVP Completion Sprint Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the AgriWise hackathon MVP from the repository's current working baseline while keeping demand, supply, price, and opportunity outputs scientifically honest and consistent across the dashboard, forecasting, mapping, markets, evidence, and chatbot experiences.

**Architecture:** FastAPI loads the versioned forecasting artifact bundle once, exposes province-resolution analytics through typed contracts, and supplies those contracts to a Next.js application. Demand serves a committed quarterly **demand-pressure index** (FIES baseline + LFS activity + seasonal indices) for all four commodities; supply and price serve observed history plus a short forecast from committed feature tables and per-commodity models; opportunity combines normalized peer-relative inputs without subtracting incompatible units.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pandas, NumPy, scikit-learn/joblib, XGBoost, pytest, Next.js 16 App Router, React, TypeScript, Tailwind CSS 4, Vitest.

**Specs and evidence:** `ml/demand/README.md` (isolated FIES/LFS reference pipeline), `ml/artifacts/reports/methodology_registry.json` + `unified_deployment_summary.csv` + per-component verdict/metric CSVs, `ml/artifacts/config/*.json` (demand registry, opportunity scoring, commodity-flow), the committed bundles under `ml/artifacts/{demand,supply,price}/` and feature tables under `ml/artifacts/prepared/`, and the checked-in contracts in `apps/api/app/schemas/forecast.py` and `apps/web/src/types/`.

> **Re-baseline note 1 (2026-09-08, commit `f07633a`).** Section 1 was rewritten to match this repository. The earlier baseline (commit `a920b90`) and some files it cited — `docs/architecture/sprint-0-audit.md`, `fies-demand-benchmark-pipeline.md`, `CODEBASE_CONTEXT.md` — describe a different codebase and are not present here. This repo is a leaner reimplementation. Sprint 2 has been split into **2a (forecast-value + evidence backend)**, **2b (opportunity engine)**, and **2c (dashboard + forecasting UI)**.
>
> **Re-baseline note 2 (2026-09-08).** The `ml/artifacts/` tree was then replaced with the mature bundle: per-commodity **`prepared/*_features.csv`** (observed + pre-engineered future rows), **`config/*.json`**, **`reports/*`** (verdicts, metrics, `methodology_registry.json`), and `demand/{rice,banana,vegetable_shared}.joblib`. This resolves the "how do we generate forecast values" question for Sprints 2a/2b — the data now exists. Sections 1–3 and Sprint 2 below reflect the new bundle. `ml/artifacts/README.md` and `ml/artifacts/market_coordinates/` were removed in that replacement and must be restored (README rewrite in Task 2a.1; market coordinates in Sprint 4).

## Global Constraints

- Supported commodities are Rice, Tomato, Red Onion, and Banana.
- Forecast analytics are province-resolution. Municipality selection may resolve to a province but must never be presented as a municipality forecast.
- Demand must be labeled **Estimated Demand Proxy** and must never be described as observed commodity consumption.
- Supply remains quarterly in metric tons; price remains monthly in PHP/kg; demand remains quarterly.
- Preserve the verdicts in the artifact bundle: `PASS`, `CAUTION`, `INSUFFICIENT_DATA`, and demand-specific `USABLE_PROXY` / `INDICATIVE_PROXY`.
- `INSUFFICIENT_DATA` components contain no generated forecast values, and missing critical inputs block opportunity scoring.
- Do not add authentication, marketplace listings, buyer-demand volumes, transactions, admin CRUD, or fabricated lower-resolution analytics.
- Do not modify `data/raw/` in place. Committed derived inputs live in `ml/artifacts/prepared/`; regenerating them is an offline step, not a runtime one.
- Each sprint ends with a runnable application, focused tests, and a concise completion report.

---

## 1. Validated Repository Baseline

This plan reflects repository state at commit `f07633a` on 2026-09-08. Repository evidence overrides older planning assumptions. Every "Implemented" claim carried over from the `a920b90` baseline is superseded by the table below.

### Module status

| Module | Current state | Evidence | Remaining work |
|---|---|---|---|
| M01 App Shell & Setup | Implemented | `apps/web/src/app/setup/page.tsx`, `AppPreferencesContext` + `preferences.tsx` (with tests), sidebar/navigation, `ComingSoon` shell for unbuilt routes | Wire real pages into shared state as they land |
| M02 Forecast Inference & Contract | **Sprint 2a complete (pending review)** | `artifact_registry.py` (full bundle: joblib + `prepared/` + `config/` + `reports/`, schema-`3.2`, `diagnostics`), `forecast_service.py` (`_demand_component`/`_series_component`/`evidence`), reshaped `forecast.py` schemas, `GET /forecast/{catalog,outlook,evidence}` | Contract hardening + optional rice benchmark (Sprint 3) |
| M03 Dashboard | **Sprint 2c done (pending review)** | `apps/web/src/app/page.tsx` + `DashboardClient.tsx` — 4-commodity outlook cards for the selected province, keyed-result state (no stale leak) | E2E QA (Sprint 6) |
| M04 Forecasting & Opportunity | **Sprint 2b + 2c done (pending review)** | `ml/forecasting/opportunity.py` (config-driven scorer), `forecast_service._opportunity()`, `forecasting/page.tsx` + `ForecastingClient.tsx` (component cards + opportunity breakdown) | "Why this result?" (Sprint 3) |
| M05 Explainability | Not implemented | no `/forecast/methodology`, no "Why this result?" component, no methodology schema | Sprint 3 |
| M06 GIS Analytics | Not implemented | `mapping/page.tsx` stub | Sprint 4 |
| M07 Curated Markets | Not started | `markets/` package dir exists but empty of logic; `ml/artifacts/market_coordinates/*.csv` was **removed** in the artifact replacement and must be restored; no `market_recommendation_config.json` in the repo; no registry, ranking, API, schema, or UI | Sprint 4 (restore coordinates first) |
| M08 Chatbot | Baseline implemented | `rag/` pipeline, `POST /rag/query`, `chat/page.tsx` (with test) | Inject structured analytics context — Sprint 5 |
| M09 Model Evidence | **Backend done (Sprint 2a, pending review)** | `ForecastService.evidence()`, `GET /forecast/evidence`, `EvidenceResponse` schema, `test_forecast_service`/`test_forecast_router` coverage | Frontend evidence page — Sprint 5 |
| M10 UX Resilience | Partial | loading/error/unsupported states in `setup` and `chat`; every other route is `ComingSoon` | Finish per real page as it lands |

Backend tests live in `apps/api/tests/`, `rag/tests/`, and `ml/demand/tests/` (not a top-level `tests/`).

### The `ml/artifacts/` bundle (post-replacement)

| Subtree | Contents | Consumed how |
|---|---|---|
| `demand/*.joblib` | `rice` (`BREAD`), `vegetable_shared` (`VEG`, backs Tomato + Red Onion), `banana` (`FRUIT`) — cross-sectional 2023 FIES household-expenditure estimators, schema `3.2` | **metadata only** (verdict / metrics / limitations / label). Never called at request time — demand values come from `prepared/` |
| `supply/*.joblib`, `price/*.joblib` | fitted `Pipeline` + `features` + `seasonal_period` + `metrics` + `verdict`. Present: `supply/{banana,red_onion}`, `price/rice`. **Being restored (decision (a)): `supply/{rice,tomato}`, `price/{tomato,banana}`** | the model for the forecast step in `prepared/*_features.csv` |
| `prepared/{commodity}_{supply,price}_features.csv` | full observed history + **future rows with `target` NaN and lags/season/rolls pre-engineered** (10 future quarters supply, up to Dec-2026 price) | `ForecastService` reads observed `target` + predicts the future rows |
| `prepared/quarterly_demand_pressure_index.csv` | observed demand-pressure index, 4 commodities × 5 provinces, 2021Q1–2025Q4 (`fies_base_index`, `economic_activity_index`, `supply_season_index`, `affordability_season_index`, `demand_pressure_index`) | the observed demand series |
| `prepared/future_demand_pressure_3q.csv` | 3 forecast quarters (2026 Q1–Q3) per commodity × province, with `confidence` (`moderate_proxy` / `low_to_moderate_shared_veg_proxy`) | the demand forecast |
| `prepared/lfs_calabarzon_activity_*.csv`, `demand_proxy_province_baseline.csv` | LFS activity inputs + FIES holdout baseline | evidence / methodology context |
| `config/commodity_demand_registry.json` | per-commodity → artifact / target / display label / specificity | demand labelling |
| `config/opportunity_scoring_config.json` | component weights, directions, 0–100 normalization policy | Sprint 2b scorer |
| `config/commodity_flow_methodology.json` | optional external inflow/outflow indicator policy | Sprint 3 methodology / optional opportunity input |
| `reports/*` | `{supply,price}_deployment_verdicts.csv`, `*_model_metrics.csv` (incl. seasonal-naive baselines), `unified_deployment_summary.csv`, `demand_validation_summary.csv`, per-commodity demand `*_validation_report.md`, `methodology_registry.json`, `dataset_inventory.csv` | `/forecast/evidence` (2a.4), `/forecast/methodology` (Sprint 3) |

**Separately:** `ml/demand/` (native XGBoost boosters + `pipeline/` for Denton benchmarking / spatial reconciliation) is the isolated FIES/LFS **reference** pipeline. It is **not wired into the API** and is not needed for serving — the committed `prepared/` index tables already carry the demand series. It stays relevant only for the optional rice physical-MT benchmark (Sprint 3).

> **Current breakage (blocks Sprint 2a.1, expected):** the new demand bundles key on `artifact_name` (`rice` / `vegetable_shared` / `banana`), not `commodity`. `ArtifactRegistry._load_bundle` does `bundle["commodity"]` and therefore **skips all three demand bundles** (`KeyError`), so the running API currently has zero demand artifacts and `test_all_committed_artifact_bundles_load` fails. Task 2a.1 fixes this by resolving demand via `config/commodity_demand_registry.json`. Supply/price bundles still carry `commodity` and load fine.

### Verified model matrix (post-replacement)

| Commodity | Demand (index) | Supply (MT, quarterly) | Price (PHP/kg, monthly) | Opportunity consequence |
|---|---|---|---|---|
| Rice | `USABLE_PROXY`; `BREAD` proxy. Index series in `prepared/`, forecast confidence `moderate_proxy` | `CAUTION`; hist gradient boosting *(joblib being restored)* | `PASS`; hist gradient boosting | Peer-relative score once 2a + 2b land |
| Tomato | `INDICATIVE_PROXY`; shared `VEG` proxy. Forecast confidence `low_to_moderate_shared_veg_proxy` | `CAUTION`; random forest *(joblib being restored)* | `CAUTION`; random forest *(joblib being restored)* | Peer-relative score after 2a + 2b |
| Red Onion | `INDICATIVE_PROXY`; same shared `VEG` proxy. **Demand series is available** | `INSUFFICIENT_DATA`; `model=None`, seasonal-naive baseline only → value-free | `INSUFFICIENT_DATA`; 972/1020 rows null → value-free | Unavailable — supply and price missing |
| Banana | `INDICATIVE_PROXY`; `FRUIT` proxy. Forecast confidence `moderate_proxy` | `CAUTION`; seasonal-naive (`model=None`) | `PASS`; random forest *(joblib being restored)* | Peer-relative score after 2a + 2b |

`INDICATIVE_PROXY` is a real verdict in `apps/api/app/schemas/forecast.py`. Red Onion is value-free for **supply and price only** — its demand proxy (shared `VEG` index) is present.

### Current API surface

| Endpoint | State | Consumer |
|---|---|---|
| `GET /forecast/catalog` | Implemented | setup, filters, future map/market views |
| `GET /forecast/outlook?commodity=&province=` | Implemented — returns `observed`/`forecast` series + unit/frequency/confidence/source/label (Sprint 2a); opportunity still `INSUFFICIENT_DATA` | dashboard and forecasting (once built) |
| `GET /forecast/evidence` | Implemented (Sprint 2a) — 12 components with model/metrics/verdict/baseline/`province_holdout` | Sprint 5 model-evidence page |
| `GET /forecast/methodology` | Not implemented | Sprint 3 explainability UI |
| `POST /rag/query` | Baseline implemented | chat page; analytics context not injected |
| `/markets/*` | Not implemented | Sprint 4 markets list/map |

---

## 2. Demand Retrieval Logic

### The demand series exists — it is committed, not computed at request time

Demand is served from two committed tables, not from the `.joblib` estimator:

| Table | Role | Shape |
|---|---|---|
| `prepared/quarterly_demand_pressure_index.csv` | observed demand-pressure index | 4 commodities × 5 provinces × 19 quarters (2021Q1–2025Q4); column `demand_pressure_index` plus its four sub-indices |
| `prepared/future_demand_pressure_3q.csv` | forecast | same keys × 3 quarters (2026 Q1–Q3); `estimated_demand_pressure_index`, `confidence`, `observed_demand=false` |

The index is **base ≈ 100**, dimensionless. Per `reports/methodology_registry.json` it is composed from a FIES 2023 household-expenditure baseline + LFS economic-activity index + seasonal supply/affordability indices — **not** the Denton/MT pipeline in `ml/demand/`. All four commodities (Red Onion included) have a series.

`ForecastService._demand_component()` (Sprint 2a) reads these tables, filters to `(commodity, province)`, returns the observed tail + the 3 forecast quarters. It **must not** call the demand `.joblib` at request time.

### What the demand `.joblib` bundles are for

`demand/{rice,vegetable_shared,banana}.joblib` are cross-sectional 2023 FIES household-expenditure estimators (`BREAD` / `VEG` / `FRUIT`), schema `3.2`. They supply, for `/forecast/evidence` and for the demand label: `selected_model`, weighted/unweighted metrics, `province_holdout`, `verdict` + `verdict_reason`, `limitations`, and (via `config/commodity_demand_registry.json`) the display label — "Cereal / Vegetable / Fruit Household Demand Proxy". The global UI label stays **Estimated Demand Proxy**.

### Contract fields already reserved

`apps/api/app/schemas/forecast.py` documents deferred work: a `demand_label` field, `data_as_of` normalization, and the `/forecast/evidence` + `/forecast/methodology` shapes. `Verdict` already includes `USABLE_PROXY` and `INDICATIVE_PROXY`.

### Demand invariants

- Always labelled **Estimated Demand Proxy**; the unit is an index, never metric tons and never "observed consumption".
- `confidence` on the forecast rows is carried verbatim (`moderate_proxy`, `low_to_moderate_shared_veg_proxy`) and mapped to the contract `Confidence` enum for opportunity scoring.
- A generic "demand−supply gap" is unsupported — demand is an index, supply is MT. Physical `supply_gap_mt` stays a rice-only optional path (Sprint 3).
- Evidence/UI copy must not imply request-time inference; served demand values are committed snapshot values.

---

## 3. Supply, Price, and Opportunity — Target Logic

Not implemented yet; this is what Sprint 2a (supply/price) and Sprint 2b (opportunity) build. The data now exists in `ml/artifacts/prepared/` and `ml/artifacts/config/`.

### Supply and price — one `_forecast_series_component()`

For a `(commodity, component)`:

1. Read `prepared/{commodity}_{component}_features.csv` (parse `date`).
2. **Observed series** = rows with non-null `target`, for the requested province, most-recent tail.
3. **Forecast** = the future rows (null `target`, `date` after the last observed date for that province), next 3 periods:
   - **model present** (`{component}/{commodity}.joblib`, verdict ≠ `INSUFFICIENT_DATA`): `bundle["model"].predict(rows[bundle["features"]])`. The pipeline's `SimpleImputer` covers the still-missing exogenous columns (`area`, `yield_proxy`, cross-series lag) in the furthest rows. `source = "learned_model:<strategy>"`.
   - **no model / `strategy == "seasonal_naive"`** (`banana` supply; `rice`/`tomato` supply and `tomato`/`banana` price *until their joblibs are restored*): use the `lag_4` (supply) / `lag_12` (price) column already on the future rows. `source = "seasonal_naive"`.
4. `frequency`: `quarterly` (supply) / `monthly` (price). `unit`: `MT` / `PHP/kg`. `data_as_of`: last observed `date`.
5. `confidence` from the bundle verdict: `PASS → HIGH`, `CAUTION → MODERATE`, else `NONE`.
6. **Red Onion**: supply `model=None` + `INSUFFICIENT_DATA`; price ~95% null `target`. Both return `verdict=INSUFFICIENT_DATA`, no `values`.
7. Quarterly consumers (opportunity) average the matching monthly price points.

Feature engineering is **not** redone at request time — the `prepared/` tables are the contract. Regenerating them is an offline step documented in the new `ml/artifacts/README.md`.

### Opportunity — driven by `config/opportunity_scoring_config.json`

That file is authoritative. As committed (schema `3.2`):

| Component (config key) | Weight | Direction | Notes |
|---|---|---|---|
| `demand_pressure_index` | 0.35 | higher_better | from the demand forecast row |
| `supply_gap_or_scarcity_index` | 0.25 | higher_better | inverse supply / scarcity |
| `price_opportunity_index` | 0.20 | higher_better | from the price forecast |
| `market_flow_dependence_index` | 0.10 | higher_better | **optional** — `config/commodity_flow_methodology.json`; omit if absent |
| `forecast_confidence_index` | 0.10 | higher_better | `HIGH=100 / MODERATE=60 / NONE=0` |

Policy from the file: normalize every input to 0–100 before combining; never subtract FIES pesos from supply MT; weights are transparent config, not learned ground truth. Renormalize weights over the components actually present (drop `market_flow` when unavailable).

- Compute across all five provinces for one commodity; select the earliest quarter shared by demand, supply, and price.
- Classifications: `HIGH_OPPORTUNITY`, `UNDERSUPPLY_LEANING`, `BALANCED`, `OVERSUPPLY_LEANING`, `SEVERE_OVERSUPPLY`.
- Any missing demand / supply / price / confidence input → `INSUFFICIENT_DATA`, no score (Red Onion always).
- The result is a peer-relative decision-support score — not ground truth, not a physical supply gap.

---

## 4. Sprint Roadmap

**State:** Sprints 0 / 0.5 / 1 done (0.5 partial). Sprint 2 (2a + 2b + 2c.1/2c.2) complete pending review on `sprint-2a/forecast-values-backend` and `sprint-2b-2c/opportunity-and-dashboard`. Next: Sprint 3. Sprints 3–6 keep their shape; the artifact drop mostly *shrinks* their scope:

| Sprint | Net effect of the artifact drop |
|---|---|
| 3 | Methodology endpoint is now a read of `reports/methodology_registry.json` + `config/*`. Demand-provenance contract split matters only if the optional rice MT benchmark is built. Task 3.2 moves ahead of 3.1. |
| 4 | Adds **Task 4.0** — restore `ml/artifacts/market_coordinates/*.csv` (removed in the drop) and author `config/market_recommendation_config.json` (never existed). No "rice-gap" map layer unless 3.1 built it. |
| 5 | Evidence UI is richer/cheaper — `reports/*` gives seasonal-naive baselines and demand `province_holdout` for free. Otherwise unchanged. |
| 6 | Demand regression is one index path (+ optional benchmark). Add `registry.diagnostics` empty check and per-component `source` / unit checks. |

## Sprint 0 — Repository and Model Audit — COMPLETE

**Modules:** M02 foundation; reuse assessment for M01–M10

**Delivered:**

- [x] Artifact inventory — `ml/artifacts/{demand,supply,price}/`, `prepared/`, `config/`, `reports/` committed; `reports/dataset_inventory.csv` lists the (external, uncommitted) raw sources
- [x] Four-commodity demand/supply/price verdict matrix — `reports/unified_deployment_summary.csv`, Section 1
- [x] Province and frequency constraints (see Global Constraints), `reports/methodology_registry.json`
- [x] RAG source inventory (`data/raw/*.pdf`)
- [ ] `ml/artifacts/README.md` was removed in the artifact replacement — rewrite for the new layout (Task 2a.1)
- [ ] `ml/artifacts/market_coordinates/` was removed — restore in Sprint 4
- [ ] `schema_version` `3.2` is *stamped* on bundles but *not validated* at load — deferred to Sprint 2a

**Exit evidence:** artifact bundle + feature tables + reports committed; `ml/demand/README.md` and `reports/methodology_registry.json` document methodology.

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

The original single Sprint 2 assumed M02/M03/M04 were "Implemented." They are registry-and-contract only (2a), nonexistent (2b), and stubs (2c). Order: **2a → 2b → 2c**. The optional rice FIES/XGBoost benchmark and physical MT `supply_gap_mt` stay **out of Sprint 2** (Sprint 3, Task 3.1).

### Recommended build order

**Step 0 — environment + artifact readiness.**

- [x] `uv sync` — restored `xgboost==3.4.1` from `uv.lock`; the demand `.joblib` bundles unpickle again (a drifted `.venv` had been silently degrading Tomato/Red Onion demand to `INSUFFICIENT_DATA`).
- [x] Regression test rewritten as `test_committed_bundle_resolves_every_commodity_component` — drives off the registry (12 commodity×component resolutions, `diagnostics == []`, shared-VEG model_id, `model_bundle` presence), not a hardcoded path list.
- [ ] **Decision (a):** restore the 4 forecasting model joblibs removed in the artifact replacement — `supply/rice`, `supply/tomato`, `price/tomato`, `price/banana`. Until they land, those four serve seasonal-naive from the `prepared/` `lag_4`/`lag_12` columns (Section 3), verdict/metrics still come from `reports/{component}_deployment_verdicts.csv`.

**Then, within Sprint 2a:**

| Order | Work | Status |
|---|---|---|
| 1 | **Registry loads the full bundle** (Task 2a.1) | ✅ done |
| 2 | **Demand values** (Task 2a.3) | ✅ done |
| 3 | **Supply + price values** (Task 2a.2) | ✅ done (seasonal-naive for the 4 not-yet-restored joblibs) |
| 4 | **`/forecast/evidence`** (Task 2a.4) | ✅ done |

All of Sprint 2a is on `sprint-2a/forecast-values-backend`, pending review. **Then 2b (opportunity engine)** — mostly wiring `config/opportunity_scoring_config.json` — **then 2c (dashboard + forecasting UI)**.

**Do not start with 2c.** The pages are only as good as the API behind them.

## Sprint 2a — Forecast-Value + Evidence Backend — COMPLETE (pending review)

**Modules:** M02, M09 backend

**Goal:** `/forecast/outlook` returns real `observed`/`forecast` series (demand index, supply MT, price PHP/kg) for every component with usable data, and a new `/forecast/evidence` exposes model provenance. No frontend work.

**Delivered on `sprint-2a/forecast-values-backend`:**

- `ml/forecasting/artifact_registry.py` — loads joblib bundles + `prepared/*.csv` + `config/*.json` + `reports/*`; `get()` falls back to `reports/{component}_deployment_verdicts.csv` when a model joblib is absent; `model_bundle()`, `feature_table()`, `report()`, `demand_pressure_*`, `opportunity_config`, `methodology` accessors; schema-`3.2` check with `strict=` mode (`ArtifactSchemaError`); `diagnostics` list; numpy → JSON coercion.
- `ml/forecasting/forecast_service.py` — `_demand_component()`, `_series_component()` (supply/price, model-or-seasonal-naive), `evidence()`; `OutlookComponentPayload` reshaped to `observed`/`forecast`/`label`/`metrics`.
- `apps/api/app/schemas/forecast.py` — `SeriesPoint`, reshaped `OutlookComponent` (dropped `values`), added `INDICATIVE_PROXY`, `EvidenceComponent` / `EvidenceResponse`.
- `apps/api/app/routers/forecast.py` — `GET /forecast/evidence`.
- `apps/web/src/types/forecast.ts` — mirrored (`SeriesPoint`, `observed`/`forecast`, `EvidenceResponse`, `INDICATIVE_PROXY`).
- `ml/artifacts/README.md` — rewritten for the new layout.

### Task 2a.1 — Registry loads the full bundle + schema-3.2 validation

- [x] Load/cache joblib bundles, `prepared/*_features.csv`, the two demand-pressure tables, `config/*.json`, `reports/*`.
- [x] Validate `schema_version == "3.2"` on bundles + `config/opportunity_scoring_config.json`; mismatch → `diagnostics` (or `ArtifactSchemaError` under `strict=True`).
- [x] Skip + record in `registry.diagnostics`; `strict=True` raises.
- [x] `vegetable_shared.joblib` loaded once, mapped to Tomato + Red Onion via `config/commodity_demand_registry.json`.
- [x] Regression test rewritten (`test_committed_bundle_resolves_every_commodity_component`).
- [x] `ml/artifacts/README.md` written.

### Task 2a.2 — Supply and price forecast values

- [x] `_series_component()`: observed `target` tail + up to 3 future periods — `model.predict()` when a joblib model is present, else seasonal-naive from `lag_4`/`lag_12` (filtered to non-null lag rows).
- [x] `unit` / `frequency` / `source` (`learned_model:<strategy>` / `seasonal_naive`) / `data_as_of` / `confidence` (`PASS→HIGH`, `CAUTION→MODERATE`, else `NONE`) / `metrics` (from `reports` fallback or joblib).
- [x] Red Onion supply and price → `INSUFFICIENT_DATA`, no series.
- [x] Deterministic — registry hands back copies; no request-time state.
- [ ] Follow-up: when decision-(a) joblibs land, `source` flips to `learned_model:*` for rice/tomato supply and tomato/banana price with no code change.

### Task 2a.3 — Demand values from the committed index

- [x] `_demand_component()` reads the two demand-pressure tables, filters `(commodity, province)`, returns observed tail + 3 forecast quarters.
- [x] `unit = "index (base~100)"`, `frequency = "quarterly"`, `source = "demand_pressure_index"`, `data_as_of` = last observed quarter.
- [x] `label` from `config/commodity_demand_registry.json` (e.g. "Cereal Household Demand Proxy"); global label stays **Estimated Demand Proxy** (UI concern); carries joblib `verdict` + `limitations`.
- [x] Forecast-row `confidence` (`moderate_proxy` / `low_to_moderate_shared_veg_proxy`) → `MODERATE`.
- [x] Never calls the demand `.joblib` at request time.

### Task 2a.4 — `GET /forecast/evidence`

- [x] `ForecastService.evidence()` — 12 components; per component: target (joblib or `methodology_registry.json`), `model` / `selected_model`, `metrics`, seasonal-naive `baseline` (from `reports/*_model_metrics.csv`), verdict + `reason`, frequency, `province_resolution`, `source`, `schema_version`, `limitations`, demand `province_holdout`.
- [x] Missing model/metrics → fields `None`/empty, verdict `INSUFFICIENT_DATA`.
- [x] Tomato and Red Onion demand share the `vegetable_shared` evidence.

**Verification (all green):**

```powershell
cd apps/api; uv run pytest tests/test_artifact_registry.py tests/test_forecast_service.py tests/test_forecast_router.py   # 37 passed
cd ../..; uv run ruff check apps/api/app ml/forecasting                                                                  # clean
cd apps/web; npm run typecheck; npm run test; npm run lint; npm run build                                                # 17 passed, clean
```

**Exit evidence:** `GET /forecast/outlook?commodity=Rice&province=Laguna` returns demand (index, `USABLE_PROXY`, `moderate` confidence), supply (MT, `seasonal_naive`), price (PHP/kg, `learned_model:hist_gradient_boosting`); `GET /forecast/evidence` returns 12 components; Red Onion supply/price value-free, its demand index present.

**Known limitations:** opportunity still `INSUFFICIENT_DATA` (Sprint 2b); tomato price seasonal-naive forecast skips periods where `lag_12` is null (starts at the first quarter with a seasonal reference).

## Sprint 2b — Opportunity Engine — COMPLETE (pending review)

**Modules:** M04 backend

**Delivered on `sprint-2b-2c/opportunity-and-dashboard`:** `ml/forecasting/opportunity.py` (`OpportunityScorer`, `OpportunityResult`), `_opportunity()` + quarterly-alignment helpers in `forecast_service.py`, `OpportunityComponent` schema extended, `apps/api/tests/test_opportunity.py`.

### Task 2b.1 — Peer-relative scoring

- [x] Components/weights/optional-flag read from `config/opportunity_scoring_config.json` — nothing hardcoded but the 0–100 method and the bands.
- [x] Computed across all five provinces; **shared quarter = the *most recent* quarter present in demand + supply + price for every province** (deviation from "earliest" — with unaligned observed histories "earliest" resolves to ~2021 and is not decision-relevant; documented).
- [x] Rank-percentile 0–100 per input; scarcity = inverse supply; `market_flow_dependence_index` dropped (no input) and weights renormalized over the remaining four (÷0.90).
- [x] `forecast_confidence_index` = mean of the three components' confidence (`HIGH=100 / MODERATE=60 / NONE=0`), used as an absolute 0–100 (not ranked).
- [x] Classifications by score band: ≥75 `HIGH_OPPORTUNITY`, ≥60 `UNDERSUPPLY_LEANING`, ≥40 `BALANCED`, ≥25 `OVERSUPPLY_LEANING`, else `SEVERE_OVERSUPPLY`.

### Task 2b.2 — Fail closed

- [x] Any province missing demand / supply / price → `INSUFFICIENT_DATA`, no score (Red Onion always — its supply & price are value-free).
- [x] Returns `breakdown` (per-component raw/score/weight) + `weights_used`.
- [x] No incompatible-unit subtraction; scorer docstring states it is peer-relative decision support.

**Verification (green):** `cd apps/api; uv run pytest tests/test_opportunity.py tests/test_forecast_service.py tests/test_forecast_router.py` — 41 passed overall; `ruff` clean.

**Exit evidence:** `/forecast/outlook` returns opportunity `score`/`classification`/`shared_quarter` (`2026-07-01`) for Rice (55.4 BALANCED), Tomato, Banana; Red Onion → `INSUFFICIENT_DATA`.

## Sprint 2c — Dashboard + Forecasting UI — 2c.1 + 2c.2 COMPLETE (pending review)

**Modules:** M03, M04 frontend, part of M10

**Delivered on `sprint-2b-2c/opportunity-and-dashboard`:**

- `apps/web/src/components/forecast/` — `verdict.ts` (badge/label/format helpers), `Sparkline.tsx` (observed→dashed-forecast inline SVG), `ComponentCard.tsx`
- `apps/web/src/app/page.tsx` + `DashboardClient.tsx` — CALABARZON dashboard
- `apps/web/src/app/forecasting/page.tsx` + `ForecastingClient.tsx` — forecasting page
- `apps/web/src/types/forecast.ts` — `OpportunityComponent` mirrored (breakdown/weights/shared_quarter)
- Tests: `apps/web/src/app/page.test.tsx`, `apps/web/src/app/forecasting/page.test.tsx`

### Task 2c.1 — CALABARZON dashboard

- [x] Fetches `/forecast/outlook` for all four commodities at the province from `AppPreferences` (province selector on the page too).
- [x] Per-commodity card: per-component latest value + verdict badge, opportunity classification + score, shared quarter, link to `/forecasting?commodity=`.
- [x] Loading / API-error / no-province states; **stale rows can't leak** — `status`/`rows` are derived from a keyed result, not set imperatively.

### Task 2c.2 — Forecasting page

- [x] Commodity + province `<select>`s synced with `AppPreferences`; seeds commodity from `?commodity=` once when preferences lack one.
- [x] Demand / supply / price `ComponentCard`s: observed vs forecast (sparkline + latest), **Estimated Demand Proxy** label + registry label, verdict, confidence, source, frequency, `data_as_of`, limitations; `resolution_note` shown.
- [x] `OpportunityCard`: score, classification, shared quarter, weighted-component breakdown table; `INSUFFICIENT_DATA` states the peer-coverage requirement plainly.
- [x] Province-resolution note on the page; no municipality framing.

**Verification (green):** `cd apps/web; npm run typecheck && npx vitest run && npm run lint && npm run build` — 23 tests passed, lint/types clean, build OK.

**Exit flow:** `Landing → Setup → Dashboard → Forecasting` works end-to-end against the live API.

**Not in this batch:** model-evidence page (Sprint 5), mapping/markets (Sprint 4), "Why this result?" (Sprint 3).

**Follow-up acceptance:** Sprint 3 must make demand provenance and any future rice benchmark mode explicit before GIS or chatbot reuse the values.

## Sprint 3 — Forecast Contract Hardening, Explainability, Optional Rice Benchmark

**Modules:** M02, M04, M05, part of M09 and M10

**Revision (artifact drop):** demand provenance is now simple — one committed index path — so Task 3.1's `prepared_proxy_snapshot` vs `fies_xgboost_benchmark` split only matters *if* the optional rice MT benchmark is built. Methodology (Task 3.2) is now largely a read of committed files: `reports/methodology_registry.json`, `config/commodity_flow_methodology.json`, `config/opportunity_scoring_config.json`.

**Files:**

- Modify: `ml/forecasting/forecast_service.py`, `apps/api/app/schemas/forecast.py`, `apps/api/app/routers/forecast.py`
- Modify: `apps/web/src/types/forecast.ts`, `apps/web/src/app/forecasting/page.tsx`
- Create: `apps/web/src/app/components/WhyThisResult.tsx`
- Test (under `apps/api/tests/`): `test_forecast_service.py`, `test_forecast_router.py`, `test_forecast_evidence.py`, `test_forecast_methodology.py`, `test_opportunity.py`; focused frontend tests

### Task 3.2 — Methodology endpoint + "Why this result?" (do this first now)

- [ ] `GET /forecast/methodology` assembled from `reports/methodology_registry.json` + `config/opportunity_scoring_config.json` + `config/commodity_flow_methodology.json` (all cached by the registry).
- [ ] "Why this result?" for demand, supply, price, opportunity: model/verdict, leading available factors, confidence reason, source, frequency, province resolution, data coverage, limitations.
- [ ] State explicitly that proxy estimates and opportunity associations are not causal findings.
- [ ] Do not invent confidence intervals; label unavailable when artifacts don't provide them.

### Task 3.1 — Optional rice FIES/XGBoost benchmark + physical `supply_gap_mt`

- [ ] Decide and record (ADR): build it, or defer. `reports/dataset_inventory.csv` confirms the raw FIES-LFS files exist externally; `ml/demand/pipeline/` is the reference implementation.
- [ ] If built: commit `data/processed/demand/` inputs, load the pipeline only when present (`demand_pipeline=None` otherwise), add contract fields distinguishing the benchmark from the index path **without** changing the `Estimated Demand Proxy` label.
- [ ] Keep physical `supply_gap_mt` rice-only; never apply it to the index-proxy commodities.
- [ ] Normalize `data_as_of` across both paths.

### Task 3.3 — Preserve analytical invariants

- [ ] Red Onion supply/price stay value-free; Red Onion opportunity unavailable (its demand index alone is not enough).
- [ ] `supply_gap_mt` (if it exists) stays rice-only.
- [ ] Opportunity scoring changes only when `config/opportunity_scoring_config.json` and `test_opportunity.py` change together.
- [ ] No stale component values after a failed or changed request.

**Verification:**

```powershell
cd apps/api; uv run pytest tests/test_forecast_service.py tests/test_forecast_router.py tests/test_forecast_evidence.py tests/test_forecast_methodology.py tests/test_opportunity.py; cd ../..
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

**Revision (artifact drop):** `ml/artifacts/market_coordinates/{CALABARZON_market_coordinates,municipality_centroids}.csv` were **removed** and must be restored (from git history — `git log --diff-filter=D --stat -- ml/artifacts/market_coordinates/` then `git checkout <commit>~1 -- <path>` — or re-sourced) as **Task 4.0** before anything else here. There is no `market_recommendation_config.json` in the repo; Sprint 4 must author the ranking config as `ml/artifacts/config/market_recommendation_config.json` (schema `3.2`, sibling of the other configs).

**Files:**

- Restore: `ml/artifacts/market_coordinates/*.csv`
- Create: `ml/artifacts/config/market_recommendation_config.json`
- Create: `apps/web/src/app/mapping/page.tsx`, `apps/web/src/gis-map/` map/data adapters
- Create: `markets/registry.py`, `markets/ranking.py`, `apps/api/app/routers/markets.py`, `apps/api/app/schemas/markets.py`
- Create: `apps/web/src/app/markets/page.tsx`, `apps/web/src/types/markets.ts`
- Test: new market registry/ranking/API tests and frontend map/market helper tests

### Task 4.1 — Build a province-honest analytics map

- [ ] Load or vendor the CALABARZON boundary assets (embed as a static asset; the CDN allowlist does not cover arbitrary tile hosts).
- [ ] Add demand, supply, price, and opportunity layers only when the selected response supports them (no rice-gap layer unless Task 3.1 built it).
- [ ] Label municipality drill-down with the source province and true province resolution.
- [ ] Loading / API error / unsupported layer / insufficient-data states; no stale map values.

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

**Revision (artifact drop):** `/forecast/evidence` (built in 2a.4) now carries seasonal-naive baselines, `improvement_vs_naive_pct`, and the demand `province_holdout` table from `reports/*` — surface these in Task 5.1. No new backend data needed here.

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
- [ ] Verify the demand index path for all four commodities; if the Sprint 3 rice MT benchmark was built, verify both modes and that `demand_pipeline=None` degrades cleanly.
- [ ] Confirm supply/price frequency + unit, province resolution, model-vs-seasonal-naive `source`, and Red Onion supply/price value-free behavior.
- [ ] Confirm opportunity reads `config/opportunity_scoring_config.json`, uses a shared quarter, renormalizes weights, and never subtracts incompatible units.
- [ ] Confirm cached registry/service behavior, `registry.diagnostics` empty, and deterministic repeated responses.

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
3. distinguish observed supply/price values, model vs. seasonal-naive forecasts, the demand-pressure index proxy, and (if built) the optional benchmarked rice MT estimate;
4. see verdict, confidence, source, frequency, unit, province resolution, data-as-of, and model evidence;
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

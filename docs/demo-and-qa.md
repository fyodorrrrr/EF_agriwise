# AgriWise — Demo Matrix & QA Checklist (Sprint 6)

## 1. Demo matrix

Three commodities chosen to show every behaviour tier. Province: **Laguna**
(swap freely — the shapes hold).

| Commodity | Demand | Supply | Price | Opportunity | What it demonstrates |
|---|---|---|---|---|---|
| **Rice** | `USABLE_PROXY` index, forecast confidence MODERATE | `CAUTION`, MT — currently `seasonal_naive` (restore `supply/rice.joblib` for `learned_model`) | `PASS`, PHP/kg, `learned_model:hist_gradient_boosting` | scored (~55, BALANCED) at the shared quarter | the fully-supported path end to end |
| **Tomato** | `INDICATIVE_PROXY` (shared VEG), confidence `low_to_moderate_shared_veg_proxy` → MODERATE | `CAUTION`, MT, `seasonal_naive` | `CAUTION`, PHP/kg, `seasonal_naive` | scored, usually `OVERSUPPLY_LEANING` | a caution-tier commodity + the shared vegetable proxy |
| **Red Onion** | `INDICATIVE_PROXY` index **is available** | `INSUFFICIENT_DATA` — value-free | `INSUFFICIENT_DATA` — value-free | `INSUFFICIENT_DATA` — no score | explicit insufficient-data instead of fabricated numbers |

Model Evidence page: Tomato and Red Onion demand show the **same** shared
`vegetable_shared` estimator; Red Onion supply/price show "no deployable model".

## 2. End-to-end user journey (manual)

Run `uv run uvicorn app.main:app --app-dir apps/api` and `npm run dev` in
`apps/web`, then, with **no account**:

1. **Landing → Setup** — pick Rice + Laguna; the choice persists (localStorage).
2. **Dashboard** — four commodity cards for Laguna; each shows per-component
   latest value + verdict and the opportunity classification. "Details →"
   deep-links to Forecasting with `?commodity=`.
3. **Forecasting** — demand/supply/price cards with observed→forecast
   sparkline, Estimated Demand Proxy label, source, confidence, `data_as_of`,
   limitations; the resolution note is shown. Opportunity card shows the
   weighted breakdown. Each card + opportunity has a **Why this result?**
   panel; a **Methodology** panel sits at the foot.
4. Switch commodity to **Red Onion** — supply, price and opportunity render
   the insufficient-data message; demand still shows its proxy series.
5. **Model Evidence** — 4 × 3 grid; verdicts, metrics vs. seasonal-naive
   baseline, demand province hold-out, limitations; missing models marked
   unavailable.
6. **Mapping** — pick an analytics layer (demand/supply/price/opportunity);
   the province list shades by relative value and shows "not available" per
   province where the layer is insufficient. The CALABARZON boundary map
   renders below.
7. **Markets** — ranked public markets for Rice + Laguna with a
   "Why recommended?" breakdown, distance caveat, coordinate-confidence
   badge, and "View on map" / "Ask AgriWise" links. Policy caveats listed.
8. **Ask AgriWise** — with Rice/Laguna selected, ask "how is rice demand
   looking?"; the answer may cite the analytics context and notes
   "Used your current Rice / Laguna analytics." Ask about Red Onion supply →
   it says the figure is not available and does not estimate.

### States to verify on each page

Loading spinner · API-error message · insufficient-data copy ·
**no stale values** after switching selection or a failed refetch (all
client pages derive render state from a keyed result, not imperative
setState) · keyboard focus order on the selects and links · mobile layout
(the `page-head` and card grids collapse to one column).

## 3. Release evidence — commands

```powershell
# Backend + RAG
uv run pytest
uv run ruff check apps/api/app ml/forecasting rag markets
# (ml/demand/ is the isolated reference pipeline and carries its own lint debt.)

# Frontend
cd apps/web
npm run typecheck
npx vitest run
npm run lint
npm run build
```

### External prerequisites

| Prerequisite | Needed for | Absent behaviour |
|---|---|---|
| `GROQ_API_KEY` in `apps/api/.env` | `POST /rag/query` generation | 503 "generation unavailable" |
| `data/processed/rag_index/` (`uv run python -m rag.ingest --rebuild`) | any `/rag/query` | 503 "RAG pipeline unavailable" |
| `ml/artifacts/` bundle | forecast/markets analytics | components report `INSUFFICIENT_DATA`; markets list is empty |
| `data/processed/demand/` FIES inputs | the optional rice MT benchmark | **deferred** (ADR-001) — never required |
| `supply/{rice,tomato}.joblib`, `price/{tomato,banana}.joblib` | learned-model forecasts for those 4 | seasonal-naive fallback (verdict/metrics still from `reports/`) |

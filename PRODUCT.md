# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two primary audiences, no account system:

- **Smallholder CALABARZON farmers** — deciding what to plant next season and where to sell,
  typically on a phone, often on a slow connection. They need a plain-language read on whether
  a commodity looks over- or under-supplied in their province and which nearby public markets
  are worth the trip.
- **Agricultural planners and researchers** — LGU / DA staff and analysts studying
  province-level supply, demand-pressure, price, and opportunity dynamics. They need the
  model provenance, verdicts, metrics vs. baseline, and methodology visible, not hidden.

The interface serves both from the same province-resolution analytics; the difference is how
much evidence each audience drills into.

## Product Purpose

AgriWise turns a versioned agricultural forecasting bundle into province-resolution demand,
supply, price, and opportunity analytics for four CALABARZON commodities (Rice, Tomato,
Red Onion, Banana), plus a curated public-market directory and a grounded Q&A assistant.

It exists to give a farmer or planner an honest, explainable outlook — "is this commodity a
balanced / oversupplied / undersupplied bet in my province, and why" — without pretending to
a precision the data does not support.

Success: an anonymous user can move through FORECAST → MAP → EXPLAIN → RECOMMEND → ASK
AGRIWISE, always able to tell observed values from forecasts, learned models from
seasonal-naive fallbacks, and a real number from an explicit "insufficient data".

## Positioning

The differentiator is **disciplined honesty about a weak-data domain**, enforced in the
contract rather than the copy:

- Demand is always an **Estimated Demand Proxy** index (base ≈ 100), never metric tons and
  never described as observed consumption.
- Analytics are province-resolution only; a municipality selection resolves to its province
  and is never presented as a municipality forecast.
- Components with insufficient data (e.g. Red Onion supply and price) carry **no** forecast
  values and block opportunity scoring — the product shows `INSUFFICIENT_DATA`, not a guess.
- Opportunity is a transparent, peer-relative, config-weighted score (0–100) across the five
  provinces — explicitly decision support, not ground truth and not a physical supply gap.
- The assistant answers only from the trusted `ForecastService` context for the current
  selection and from curated documents, and says "not available" rather than estimating.

A neighboring "ag analytics dashboard" could copy the screens; it could not truthfully copy
the claim that every number is traceable to a committed artifact with a stated verdict and
limitations.

## Operating Context

- **Region / scope:** CALABARZON (Cavite, Laguna, Batangas, Rizal, Quezon), four commodities.
- **Frequencies / units:** supply quarterly in MT; price monthly in PHP/kg; demand quarterly
  as a dimensionless index. Verdict vocabulary: `PASS`, `CAUTION`, `INSUFFICIENT_DATA`,
  and demand-specific `USABLE_PROXY` / `INDICATIVE_PROXY`.
- **Surfaces:** Dashboard, Setup, Forecasting, Mapping, Markets, Chat (Ask AgriWise),
  Model Evidence — a left sidebar on desktop that becomes a fixed bottom tab bar on mobile.
- **Data flow:** FastAPI loads the versioned forecasting snapshot once at startup and serves
  typed contracts; the Next.js app renders them. Client pages derive render state from a
  keyed result so stale values never leak across a selection change or failed refetch.
- **Usage scene:** no login; crop + province preference persists in `localStorage`. Expected
  on low bandwidth and small screens for the farmer audience.
- **Evaluation scene (demo):** a scripted walkthrough on Laguna using Rice (fully supported),
  Tomato (caution tier), and Red Onion (insufficient-data), documented in
  `docs/demo-and-qa.md`.

## Capabilities and Constraints

Confirmed capabilities:

- Province-resolution outlook (demand / supply / price / opportunity) for 4 commodities × 5
  provinces, with observed→forecast series, verdict, confidence, source, unit, frequency,
  `data_as_of`, and limitations per component.
- "Why this result?" per component and a methodology panel; Model Evidence page with a 4×3
  matrix (model, metrics vs. seasonal-naive baseline, demand province hold-out).
- Mapping page: per-layer province-resolution values shaded by relative value beside a
  CALABARZON boundary map. **Open follow-up:** true on-map choropleth (tinted polygons) and a
  `?market=` map pin are not built yet — analytics render as a shaded list beside the map.
- Curated market directory with transparent, config-weighted ranking, "Why recommended?"
  breakdown, coordinate-confidence badges, and stated policy caveats. ~40 of 131 curated
  entries carry coordinates; name-only rows are dropped, not faked.
- Ask AgriWise: RAG over curated PDFs + injected trusted analytics context for the current
  selection; returns citations and an `analytics_context_used` flag.

Hard constraints (bind code and contracts):

- No authentication, marketplace listings, buyer-demand volumes, transactions, admin CRUD,
  or fabricated lower-resolution analytics.
- `data/raw/` is never modified in place; derived inputs live in `ml/artifacts/prepared/`
  and are regenerated offline, not at request time.
- The demand `.joblib` estimators are metadata-only and must never be called at request time.
- No invented confidence intervals anywhere.
- The optional rice FIES/XGBoost physical-MT benchmark is deferred (ADR-001); `demand.unit`
  stays an index and no `supply_gap_mt` appears in the contract.

Terminology: "Estimated Demand Proxy", "demand-pressure index", "opportunity classification"
(`HIGH_OPPORTUNITY`, `UNDERSUPPLY_LEANING`, `BALANCED`, `OVERSUPPLY_LEANING`,
`SEVERE_OVERSUPPLY`), "province resolution", "seasonal-naive fallback".

## Stack

Existing codebase, not a user decision: Next.js 16 (App Router) + React 19 + TypeScript +
Tailwind CSS 4 + Vitest on the frontend; Python 3.12 + FastAPI + Pydantic + pandas/NumPy +
scikit-learn/joblib (+ optional XGBoost) + pytest on the backend. Monorepo: `apps/web`,
`apps/api`, with `ml/`, `markets/`, `rag/` Python packages installed editable via `uv`.

## Brand Commitments

**Explicitly non-binding.** The name "AgriWise" and the current visual world (forest-green
accent, second "leaf" green, light-theme-only, Plus Jakarta Sans / JetBrains Mono, pill
buttons and chips, the token set in `apps/web/src/app/globals.css`) are a starting point the
team is willing to replace. Status meanings (warn / info / danger as the only non-greens,
"meaning never decoration") are a sensible convention but not a mandate.

Any future visual world must still carry the product truth above: the honesty conventions,
the verdict vocabulary, province-resolution framing, and the observed-vs-forecast /
insufficient-data distinctions are product, not style.

## Evidence on Hand

Real, in-repo:

- Committed forecasting bundle: `ml/artifacts/{demand,supply,price}/*.joblib`,
  `ml/artifacts/prepared/*.csv` (observed + pre-engineered future rows),
  `ml/artifacts/config/*.json` (demand registry, opportunity scoring, commodity flow,
  market recommendation), `ml/artifacts/reports/*` (verdicts, metrics, `methodology_registry.json`).
- Curated market coordinates under `ml/artifacts/market_coordinates/*.csv`.
- RAG source PDFs in `data/raw/`; index built to `data/processed/rag_index/` (gitignored).
- Test evidence: backend 111 tests, frontend 31 tests green as of Sprint 6;
  `apps/api/tests/test_regression_matrix.py`, `test_forecast_invariants.py`.
- `docs/demo-and-qa.md` (demo matrix + manual journey + state checklist),
  `docs/architecture/Sprints_plan.md`, `docs/architecture/adr-001-rice-fies-xgboost-benchmark.md`.

Absences future work must not fabricate: no user testimonials, no adoption or usage numbers,
no partner/LGU endorsements, no pricing or licensing, no deployment/uptime claims. Red Onion
supply and price have no deployable model — do not invent values for them.

External prerequisites (not in repo): `GROQ_API_KEY` for `/rag/query` generation; the raw
FIES/LFS inputs for the deferred rice benchmark.

## Product Principles

1. **Traceable or absent.** Every displayed number resolves to a committed artifact with a
   verdict and stated limitations, or it is shown as `INSUFFICIENT_DATA`. Never split the
   difference with a soft guess.
2. **Name the method.** Observed vs. forecast, learned model vs. seasonal-naive, index vs.
   physical unit, province vs. municipality — the distinction is always visible, never
   smoothed away for a cleaner screen.
3. **Two audiences, one truth.** A farmer gets the plain read; a planner gets the evidence
   behind it. The same analytics serve both — evidence is progressive disclosure, not a
   separate product.
4. **Decision support, not authority.** Opportunity scores and market rankings are
   peer-relative and config-transparent; the UI must keep them from reading as ground truth.
5. **Works on a slow phone.** The farmer path assumes low bandwidth and a small screen;
   loading, error, empty, and insufficient-data states are first-class on every page.

## Accessibility & Inclusion

No formal standard was established as a contractual requirement, but the shipped baseline
sets the floor to hold: visible `:focus-visible` outlines, keyboard focus order on selects
and links, 44px touch targets under `(hover: none)`, 16px inputs to prevent iOS zoom,
`prefers-reduced-motion` handling, and a mobile layout that collapses grids and the
`page-head` to one column. Plain-language copy matters for the farmer audience; English is
the only locale so far (a Filipino/Tagalog locale is a plausible future need, not a
commitment).

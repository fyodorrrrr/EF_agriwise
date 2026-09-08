# ADR-001 — Defer the optional rice FIES/XGBoost MT benchmark

- **Status:** Accepted (Sprint 3, 2026-09-09)
- **Context:** Sprint 3, Task 3.1

## Decision

**Do not build the rice FIES/XGBoost benchmark path or `supply_gap_mt` for the MVP.**
`/forecast/outlook` serves demand only as the committed quarterly
demand-pressure **index** (Section 2) for all four commodities.

## Why

1. **Inputs are not in the repo and are large.** The path needs the processed
   2023 FIES/LFS household table plus spatial/temporal benchmark CSVs under
   `data/processed/demand/`. `reports/dataset_inventory.csv` shows the raw
   sources run to hundreds of MB and are intentionally external.
2. **The reference pipeline is wired to fail.** `ml/demand/pipeline/run_pipeline.py`
   "intentionally fails at the inference boundary" in this checkout because the
   regional LFS table does not carry Model B's 129 features.
3. **It adds request-time risk for one commodity.** An XGBoost `predict()` path,
   a second `data_as_of` representation (year vs date), and a unit switch
   (index → MT) — all rice-only — for marginal MVP value.
4. **The committed index already covers the honest requirement.** Every
   commodity has an *Estimated Demand Proxy* series with a verdict and a
   confidence label. Nothing is fabricated by leaving the benchmark out.

## Consequences

- `demand.unit` is always `index (base~100)`; there is no `supply_gap_mt`
  anywhere in the contract. Sprint 3, Task 3.3 keeps this invariant.
- Definition of Done item 3's "optional benchmarked rice estimate" is
  explicitly **not delivered** and is called out as such in Sprint 6.
- **Revisit when** `data/processed/demand/` inputs are committed and
  `ml/demand/pipeline` runs clean. At that point: gate it behind
  `demand_pipeline is not None`, add a `provenance` field
  (`prepared_proxy_snapshot` vs `fies_xgboost_benchmark`) without changing the
  `Estimated Demand Proxy` label, and keep `supply_gap_mt` rice-only.

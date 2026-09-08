# `ml/artifacts/` — the forecast-service artifact bundle

Loaded once at API startup by `ml/forecasting/artifact_registry.py`
(`ArtifactRegistry.load`) and served through `GET /forecast/outlook` and
`GET /forecast/evidence`. Schema version: **`3.2`** (stamped on every joblib
bundle and on `config/opportunity_scoring_config.json`).

> **Not** the same as `ml/demand/`. That directory is the isolated FIES/LFS
> reference pipeline (Denton benchmarking, spatial reconciliation) and is
> **not** wired into the API. The demand series the API serves comes from
> `prepared/*_demand_pressure*` in this directory.

## Layout

```text
ml/artifacts/
  demand/
    rice.joblib              # BREAD  cross-sectional 2023 FIES expenditure estimator
    vegetable_shared.joblib  # VEG    backs BOTH Tomato and Red Onion
    banana.joblib            # FRUIT
  supply/
    {commodity_slug}.joblib  # fitted Pipeline (or model=None for seasonal-naive)
  price/
    {commodity_slug}.joblib
  prepared/
    {slug}_supply_features.csv    # observed target + pre-engineered future rows
    {slug}_price_features.csv
    {slug}_price_panel.csv        # thin observed-only view (unused by the API)
    quarterly_demand_pressure_index.csv   # observed demand index, 4x5 provinces
    future_demand_pressure_3q.csv         # 3 forecast quarters + confidence
    lfs_calabarzon_activity_{monthly,quarterly}.csv
    demand_proxy_province_baseline.csv
  config/
    commodity_demand_registry.json   # commodity -> demand artifact / target / label
    opportunity_scoring_config.json   # Sprint 2b component weights + policy
    commodity_flow_methodology.json
  reports/
    {supply,price}_deployment_verdicts.csv   # verdict + metrics, ALL 4 commodities
    {supply,price,demand_proxy}_model_metrics.csv  # incl. seasonal-naive baselines
    demand_validation_summary.csv
    unified_deployment_summary.csv
    {rice,vegetable_shared,banana}_validation_report.md
    methodology_registry.json
    dataset_inventory.csv            # the (external, uncommitted) raw sources
```

`commodity_slug` = the commodity lowercased with spaces as underscores
(`Red Onion` -> `red_onion`).

## How the registry uses it

| Need | Source |
|---|---|
| demand verdict / metrics / label / `province_holdout` | `demand/*.joblib` resolved via `config/commodity_demand_registry.json` |
| demand observed + forecast values | `prepared/quarterly_demand_pressure_index.csv` + `future_demand_pressure_3q.csv` — **never the joblib at request time** |
| supply / price verdict + metrics | `{component}/{slug}.joblib` if present, else the `reports/{component}_deployment_verdicts.csv` row |
| supply / price observed + forecast values | `prepared/{slug}_{component}_features.csv`: observed `target`, then `model.predict()` on the future rows when a joblib model exists, else the `lag_4` / `lag_12` column (seasonal-naive) |
| opportunity config (Sprint 2b) | `config/opportunity_scoring_config.json` |
| `/forecast/evidence`, `/forecast/methodology` | `reports/*` + `config/commodity_flow_methodology.json` |

A missing file is never fatal — the affected component falls back to
`INSUFFICIENT_DATA` and the reason is recorded in `registry.diagnostics`.
`ArtifactRegistry.load(..., strict=True)` turns a schema-version mismatch into
an `ArtifactSchemaError` (used by CI / tests).

## Regenerating

The joblib bundles, `prepared/` tables, and `reports/` are produced **offline**
by the training notebook (external to this repo) and its promotion step. The
API does no feature engineering or model training at request time — it reads
these committed files. When models are retrained, re-promote the whole
`ml/artifacts/` tree together so verdicts, metrics, and feature tables stay
consistent.

Raw PSA / FIES-LFS sources (listed in `reports/dataset_inventory.csv`) are
large and stay **out of the repo**.

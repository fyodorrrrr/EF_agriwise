# Forecast-service artifact registry

This directory holds the lightweight per-commodity model bundles consumed by
`ml/forecasting/artifact_registry.py` at API startup, and served through
`GET /forecast/outlook`.

**This is not the same thing as `ml/demand/artifacts/`.** Two unrelated
model artifact stores currently exist in this repo:

| | `ml/artifacts/` (this directory) | `ml/demand/artifacts/` |
|---|---|---|
| Format | `joblib`-pickled dict bundles (`{commodity}.joblib`) | Native XGBoost JSON boosters + separate feature/parameter manifest JSON files |
| Consumed by | `ml/forecasting/artifact_registry.py` -> `ForecastService` -> `/forecast/outlook` | `ml/demand/pipeline/inference.py` (`ModelBInference`) -> the isolated Denton/spatial-reconciliation demand pipeline |
| Covers | Demand, supply, and price components for all 4 commodities | Household-level FIES-LFS `BREAD`/`VEG` expenditure models only ("Model B") |
| Produced by | `trainings_file/AgriWise_Complete_Modeling_V3_2.ipynb`'s final promotion cell (trains GradientBoosting/XGBoost/HistGB/RandomForest candidates, races them, then copies the winning bundles here with the schema below) | `ml/demand/pipeline/train_quarterly_101.py` / `train_vegetable_101.py` / `train_vegetable_129.py`, documented in depth in `ml/demand/README.md` and `ross'_work/review_bundle/` |
| Validation style | Numeric verdict tiers (`USABLE_PROXY` / `INDICATIVE_PROXY` / `CAUTION` / `PASS` / `INSUFFICIENT_DATA`) based on weighted R2/WAPE/MASE | Structural fail-closed assertions (feature-manifest integrity, no leakage, finite/non-negative predictions) -- see `ml/demand/README.md` |

If you're looking for the mature, heavily-audited FIES/LFS quarterly demand
pipeline (Denton benchmarking, spatial reconciliation, provenance-recovered
feature formulas), that lives in `ml/demand/` -- start with
`ml/demand/README.md`, not here.

## Layout

```text
ml/artifacts/
  demand/{rice,tomato,red_onion,banana}.joblib
  supply/{rice,tomato,red_onion,banana}.joblib   (one per commodity with sufficient data)
  price/{rice,tomato,red_onion,banana}.joblib    (one per commodity with sufficient data)
```

Each bundle is a `joblib.dump()`'d dict with, at minimum, `commodity`
(Title Case, matching `ml/forecasting/domain.py::COMMODITIES` exactly),
`model_id`, `verdict`, `metrics`, and `limitations` -- see
`ml/forecasting/artifact_registry.py` for the exact contract and
`apps/api/tests/test_artifact_registry.py` for a worked example.

The `demand/tomato.joblib` and `demand/red_onion.joblib` bundles are two
separate files sharing one trained model (FIES does not distinguish the two
commodities in its `VEG` expenditure category), not an alias -- the registry
keys strictly on the `commodity` field inside each file.

## Regenerating

Run `trainings_file/AgriWise_Complete_Modeling_V3_2.ipynb` end to end from
the **same Python environment `EF_agriwise` runs on** (its `.venv`, via an
`ipykernel` registered against it) -- joblib-pickled sklearn/XGBoost
estimators are not guaranteed compatible across differing scikit-learn/numpy
versions, and a mismatched environment will make bundles here fail to load
silently (`ArtifactRegistry` treats a broken bundle as simply absent, logging
a warning rather than raising). The notebook's final cell detects this
`EF_agriwise` checkout automatically (as a sibling of `trainings_file/`) and
promotes bundles here; it skips gracefully with a printed message if
`EF_agriwise` isn't found.

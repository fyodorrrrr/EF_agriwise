# Bread vs vegetable 101-feature review bundle

This is a small, inspection-only bundle for comparing the matched quarterly-safe bread
and vegetable XGBoost experiments. It contains no raw microdata and no full training
tables.

## Included files

| File | Purpose |
|---|---|
| `bread_train_101.py` | Current bread 101-feature training and evaluation procedure. |
| `vegetable_train_101.py` | Current vegetable 101-feature training; it reuses bread-preprocessed rows and substitutes raw `VEG` for `BREAD`. |
| `bread_preprocessing_provenance.py` | Recovered historical FIES-LFS feature-preparation provenance. |
| `bread_101_features.json`, `vegetable_101_features.json` | Ordered predictor manifests. |
| `bread_101_parameters.json`, `vegetable_101_parameters.json` | XGBoost parameter dictionaries. |
| `validated_quarterly_lfs_feature_contract.csv` | The source of the 101 quarterly-safe features. |
| `bread_101_evaluation.md`, `vegetable_101_evaluation.md` | Evaluation reports. |
| `target_summary_comparison.csv` | Same-sample target distribution comparison. |
| `training_table_manifest.md` | Training-source paths, hashes, schema summary, preprocessing, and split evidence. |

## Scope

The comparison is deliberately limited to `xgboost_model_b_quarterly_101` and
`xgboost_vegetable_quarterly_101`. Do not compare the separate 129-feature vegetable
experiment here: it uses features unavailable for general quarterly LFS inference.

## Key result

For the matched 101-feature models, the household rows, ordered predictors, split,
survey-weight treatment, parameter dictionary, and evaluation function are shared.
The target is the intended difference: `BREAD` versus raw FIES `VEG`.

# Quarterly 101-feature Model B retraining

Training completed using the recovered 2018 table plus the exact recovered 2023 split (`test_size=0.20`, `random_state=42`). `SURVEY_WEIGHT` was used only as XGBoost `sample_weight`. No PUFPWGTPRV aggregation, Denton benchmarking, or spatial reconciliation was performed.

## Dataset

- Features: 101
- Model B training households: 13,877
- Held-out 2023 households: 1,632
- 2018 households: 7,353
- Non-held-out 2023 households: 6,524

## Metrics

| metric | original 129-feature model | new 101-feature model | difference |
|---|---:|---:|---:|
| R2 | 0.452989 | 0.445996 | -0.006993 |
| MAE | 6503.24 | 6540.17 | +36.94 |
| RMSE | 9189.52 | 9248.08 | +58.55 |
| normalized MAE (%) | 25.3768 | 25.5209 | +0.1441 pp |
| aggregate bias (%) | -1.0565 | -1.7019 | -0.6454 pp |

## New-model sanity check

- Weighted target mean: 25,626.72
- Weighted prediction mean: 25,190.57
- Minimum prediction: 9,554.76
- Maximum prediction: 75,717.92
- Negative predictions: 0
- Non-finite predictions: 0

## Quarterly inference

2025 Q3 inference succeeded for 11,174 households. All 101 features aligned to the saved manifest and all predictions were finite. These are household BREAD-expenditure predictions only; they are not regional demand estimates.

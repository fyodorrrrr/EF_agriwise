# Demand-proxy validation report -- Rice (via BREAD proxy)

Artifact: `demand/rice.joblib` | Target column: `BREAD` | Model selected: **XGBRegressor_regularized**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | CV median weighted R2 | CV median WAPE | final-holdout weighted R2 | weighted MAE | weighted RMSE |
|---|---|---|---|---|---|
| GradientBoostingRegressor | 0.528 | 23.4% | 0.544 | 6141.9 | 8168.7 |
| GradientBoostingRegressor_huber | 0.527 | 23.5% | 0.541 | 6089.4 | 8201.1 |
| GradientBoostingRegressor_log1p | 0.526 | 23.5% | 0.526 | 6106.9 | 8333.0 |
| XGBRegressor | 0.531 | 23.6% | 0.537 | 6170.1 | 8233.7 |
| XGBRegressor_regularized **(selected)** | 0.531 | 23.6% | 0.537 | 6168.2 | 8233.3 |
| HistGradientBoostingRegressor_poisson | 0.516 | 23.6% | 0.542 | 6163.2 | 8187.2 |

Tuning note: selected by 3-fold province+target-quantile stratified CV on the 75% training partition; final 25% holdout was untouched until selection

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.537 | 0.548 |
| MAE | 6168.2 | 6185.6 |
| RMSE | 8233.3 | 8299.6 |
| WAPE | -- | 23.24% |
| sMAPE | -- | 23.77% |
| MAPE | -- | 27.24% |
| MASE (vs. province-mean naive) | -- | 0.654 |
| Bias | -- | -393.2 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = -0.12%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.522 | 6135.0 |
| Cavite | 0.492 | 6651.9 |
| Laguna | 0.465 | 6684.0 |
| Quezon | 0.458 | 6806.1 |
| Rizal | 0.536 | 6524.8 |

## Proxy-mapping caveat

`BREAD` is a household expenditure-category proxy for **Rice**, not a measurement of physical purchase quantity of that commodity. Treat outputs as directional/indicative demand pressure, not literal commodity volume.

## Verdict

**USABLE_PROXY** -- weighted R2 and/or WAPE meet the usable-proxy bar

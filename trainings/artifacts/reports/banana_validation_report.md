# Demand-proxy validation report -- Banana (via FRUIT proxy)

Artifact: `demand/banana.joblib` | Target column: `FRUIT` | Model selected: **GradientBoostingRegressor_regularized**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | weighted R2 | weighted MAE | weighted RMSE | normalized MAE % | aggregate bias % |
|---|---|---|---|---|---|
| GradientBoostingRegressor | 0.289 | 2510.6 | 3778.2 | 50.1% | 0.29% |
| XGBRegressor | 0.314 | 2491.9 | 3710.8 | 49.8% | 0.30% |
| GradientBoostingRegressor_regularized **(selected)** | 0.319 | 2479.0 | 3697.4 | 49.5% | 0.19% |
| XGBRegressor_regularized | 0.314 | 2491.9 | 3710.4 | 49.8% | 0.30% |

Tuning note: attempted regularized GB/XGB variants; kept the best-scoring variant

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.319 | 0.335 |
| MAE | 2479.0 | 2361.2 |
| RMSE | 3697.4 | 3567.8 |
| WAPE | -- | 48.68% |
| sMAPE | -- | 50.67% |
| MAPE | -- | 102.00% |
| MASE (vs. province-mean naive) | -- | 0.790 |
| Bias | -- | -47.6 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = 0.19%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.225 | 2560.0 |
| Cavite | 0.232 | 2737.8 |
| Laguna | 0.330 | 2518.1 |
| Quezon | 0.370 | 1787.9 |
| Rizal | 0.290 | 2814.3 |

## Proxy-mapping caveat

`FRUIT` is a household expenditure-category proxy for **Banana**, not a measurement of physical purchase quantity of that commodity. Treat outputs as directional/indicative demand pressure, not literal commodity volume.

## Verdict

**INDICATIVE_PROXY** -- weak explanatory power; use for relative/directional signal, not precise point forecasts

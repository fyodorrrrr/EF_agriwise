# Demand-proxy validation report -- Vegetable -- Tomato & Red Onion (via VEG proxy)

Artifact: `demand/vegetable_shared.joblib` | Target column: `VEG` | Model selected: **XGBRegressor**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | weighted R2 | weighted MAE | weighted RMSE | normalized MAE % | aggregate bias % |
|---|---|---|---|---|---|
| GradientBoostingRegressor | 0.233 | 3325.7 | 5059.2 | 43.8% | 1.55% |
| XGBRegressor **(selected)** | 0.256 | 3264.7 | 4982.3 | 43.0% | 1.07% |
| GradientBoostingRegressor_regularized | 0.252 | 3280.1 | 4994.1 | 43.2% | 1.36% |
| XGBRegressor_regularized | 0.256 | 3265.0 | 4982.8 | 43.0% | 1.07% |

Tuning note: attempted regularized GB/XGB variants; none improved on the original candidates, original kept

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.256 | 0.271 |
| MAE | 3264.7 | 3094.7 |
| RMSE | 4982.3 | 4787.2 |
| WAPE | -- | 42.02% |
| sMAPE | -- | 42.66% |
| MAPE | -- | 66.18% |
| MASE (vs. province-mean naive) | -- | 0.842 |
| Bias | -- | 100.4 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = 1.07%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.153 | 3085.7 |
| Cavite | 0.260 | 3394.4 |
| Laguna | 0.211 | 3561.6 |
| Quezon | 0.235 | 2422.0 |
| Rizal | 0.198 | 3816.8 |

## Proxy-mapping caveat

`VEG` is a broad FIES vegetable-expenditure category shared by Tomato and Red Onion. This model does not and cannot distinguish between the two commodities; it is deployed identically under both.

## Verdict

**INDICATIVE_PROXY** -- weak explanatory power; use for relative/directional signal, not precise point forecasts

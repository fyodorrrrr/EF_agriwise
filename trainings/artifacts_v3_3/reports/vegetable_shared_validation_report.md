# Demand-proxy validation report -- Vegetable -- Tomato & Red Onion (via VEG proxy)

Artifact: `demand/vegetable_shared.joblib` | Target column: `VEG` | Model selected: **GradientBoostingRegressor**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | CV median weighted R2 | CV median WAPE | final-holdout weighted R2 | weighted MAE | weighted RMSE |
|---|---|---|---|---|---|
| GradientBoostingRegressor **(selected)** | 0.261 | 42.0% | 0.196 | 3426.2 | 6016.0 |
| GradientBoostingRegressor_huber | 0.250 | 40.8% | 0.195 | 3332.0 | 6018.4 |
| GradientBoostingRegressor_log1p | 0.197 | 41.3% | 0.158 | 3378.6 | 6156.3 |
| XGBRegressor | 0.256 | 41.7% | 0.201 | 3399.8 | 5994.8 |
| XGBRegressor_regularized | 0.257 | 41.6% | 0.201 | 3399.9 | 5994.8 |
| HistGradientBoostingRegressor_poisson | 0.245 | 41.7% | 0.163 | 3443.7 | 6136.1 |

Tuning note: selected by 3-fold province+target-quantile stratified CV on the 75% training partition; final 25% holdout was untouched until selection

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.196 | 0.194 |
| MAE | 3426.2 | 3305.3 |
| RMSE | 6016.0 | 5770.4 |
| WAPE | -- | 43.48% |
| sMAPE | -- | 43.66% |
| MAPE | -- | 73.00% |
| MASE (vs. province-mean naive) | -- | 0.863 |
| Bias | -- | -120.6 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = -1.47%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.161 | 3106.3 |
| Cavite | 0.256 | 3403.8 |
| Laguna | 0.198 | 3572.5 |
| Quezon | 0.212 | 2469.3 |
| Rizal | 0.178 | 3856.4 |

## Proxy-mapping caveat

`VEG` is a broad FIES vegetable-expenditure category shared by Tomato and Red Onion. This model does not and cannot distinguish between the two commodities; it is deployed identically under both.

## Verdict

**INDICATIVE_PROXY** -- weak explanatory power; use for relative/directional signal, not precise point forecasts

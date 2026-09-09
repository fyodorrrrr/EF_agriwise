# Demand-proxy validation report -- Vegetable -- Tomato & Red Onion (via VEG proxy)

Artifact: `demand/vegetable_shared.joblib` | Target column: `VEG` | Model selected: **GradientBoostingRegressor__t1**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | CV median weighted R2 | CV median WAPE | final-holdout weighted R2 | weighted MAE | weighted RMSE |
|---|---|---|---|---|---|
| GradientBoostingRegressor | 0.261 | 42.0% | 0.196 | 3426.2 | 6016.0 |
| GradientBoostingRegressor__t1 **(selected)** | 0.265 | 41.5% | 0.197 | 3415.2 | 6010.9 |
| GradientBoostingRegressor_huber | 0.250 | 40.8% | 0.195 | 3332.0 | 6018.4 |
| GradientBoostingRegressor_huber__t1 | 0.256 | 40.7% | 0.189 | 3339.8 | 6040.4 |
| GradientBoostingRegressor_log1p | 0.197 | 41.3% | 0.158 | 3378.6 | 6156.3 |
| GradientBoostingRegressor_log1p__t1 | 0.193 | 41.2% | 0.136 | 3381.5 | 6234.1 |
| XGBRegressor | 0.256 | 41.7% | 0.201 | 3399.8 | 5994.8 |
| XGBRegressor__t1 | 0.257 | 41.6% | 0.201 | 3399.9 | 5994.8 |
| HistGradientBoostingRegressor_poisson | 0.245 | 41.7% | 0.163 | 3443.7 | 6136.1 |
| HistGradientBoostingRegressor_poisson__t1 | 0.251 | 41.5% | 0.180 | 3432.7 | 6075.7 |

Tuning note: selected, together with its hyperparameters, by 3-fold province+target-quantile stratified CV over a small per-family grid on the 75% training partition; final 25% holdout was untouched until selection

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.197 | 0.200 |
| MAE | 3415.2 | 3291.0 |
| RMSE | 6010.9 | 5747.5 |
| WAPE | -- | 43.29% |
| sMAPE | -- | 43.85% |
| MAPE | -- | 74.30% |
| MASE (vs. province-mean naive) | -- | 0.859 |
| Bias | -- | -110.4 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = -1.31%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.167 | 3074.3 |
| Cavite | 0.261 | 3395.1 |
| Laguna | 0.228 | 3523.4 |
| Quezon | 0.237 | 2417.5 |
| Rizal | 0.209 | 3780.6 |

## Proxy-mapping caveat

`VEG` is a broad FIES vegetable-expenditure category shared by Tomato and Red Onion. This model does not and cannot distinguish between the two commodities; it is deployed identically under both.

## Verdict

**INDICATIVE_PROXY** -- weak explanatory power; use for relative/directional signal, not precise point forecasts

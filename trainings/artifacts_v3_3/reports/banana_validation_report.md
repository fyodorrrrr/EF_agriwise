# Demand-proxy validation report -- Banana (via FRUIT proxy)

Artifact: `demand/banana.joblib` | Target column: `FRUIT` | Model selected: **GradientBoostingRegressor_huber**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | CV median weighted R2 | CV median WAPE | final-holdout weighted R2 | weighted MAE | weighted RMSE |
|---|---|---|---|---|---|
| GradientBoostingRegressor | 0.260 | 49.6% | 0.249 | 2526.3 | 3772.5 |
| GradientBoostingRegressor_huber **(selected)** | 0.282 | 47.4% | 0.278 | 2405.1 | 3699.6 |
| GradientBoostingRegressor_log1p | 0.234 | 47.5% | 0.251 | 2361.2 | 3767.6 |
| XGBRegressor | 0.269 | 49.4% | 0.248 | 2521.6 | 3774.7 |
| XGBRegressor_regularized | 0.269 | 49.4% | 0.249 | 2520.4 | 3772.2 |
| HistGradientBoostingRegressor_poisson | 0.245 | 50.0% | 0.223 | 2558.4 | 3836.1 |

Tuning note: selected by 3-fold province+target-quantile stratified CV on the 75% training partition; final 25% holdout was untouched until selection

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.278 | 0.295 |
| MAE | 2405.1 | 2300.1 |
| RMSE | 3699.6 | 3560.9 |
| WAPE | -- | 47.59% |
| sMAPE | -- | 50.04% |
| MAPE | -- | 80.78% |
| MASE (vs. province-mean naive) | -- | 0.779 |
| Bias | -- | -369.8 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = -5.47%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.215 | 2480.6 |
| Cavite | 0.240 | 2625.1 |
| Laguna | 0.315 | 2453.4 |
| Quezon | 0.353 | 1742.0 |
| Rizal | 0.258 | 2764.3 |

## Proxy-mapping caveat

`FRUIT` is a household expenditure-category proxy for **Banana**, not a measurement of physical purchase quantity of that commodity. Treat outputs as directional/indicative demand pressure, not literal commodity volume.

## Verdict

**INDICATIVE_PROXY** -- weak explanatory power; use for relative/directional signal, not precise point forecasts

# Demand-proxy validation report -- Banana (via FRUIT proxy)

Artifact: `demand/banana.joblib` | Target column: `FRUIT` | Model selected: **HistGradientBoostingRegressor_poisson__t1**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | CV median weighted R2 | CV median WAPE | final-holdout weighted R2 | weighted MAE | weighted RMSE |
|---|---|---|---|---|---|
| GradientBoostingRegressor | 0.260 | 49.6% | 0.249 | 2526.3 | 3772.5 |
| GradientBoostingRegressor__t1 | 0.280 | 49.7% | 0.278 | 2501.7 | 3698.2 |
| GradientBoostingRegressor_huber | 0.282 | 47.4% | 0.278 | 2405.1 | 3699.6 |
| GradientBoostingRegressor_huber__t1 | 0.280 | 47.3% | 0.285 | 2388.5 | 3680.8 |
| GradientBoostingRegressor_log1p | 0.234 | 47.5% | 0.251 | 2361.2 | 3767.6 |
| GradientBoostingRegressor_log1p__t1 | 0.223 | 47.4% | 0.248 | 2347.1 | 3775.2 |
| XGBRegressor | 0.269 | 49.4% | 0.248 | 2521.6 | 3774.7 |
| XGBRegressor__t1 | 0.269 | 49.4% | 0.249 | 2520.4 | 3772.2 |
| HistGradientBoostingRegressor_poisson | 0.245 | 50.0% | 0.223 | 2558.4 | 3836.1 |
| HistGradientBoostingRegressor_poisson__t1 **(selected)** | 0.286 | 49.0% | 0.254 | 2529.1 | 3760.8 |

Tuning note: selected, together with its hyperparameters, by 3-fold province+target-quantile stratified CV over a small per-family grid on the 75% training partition; final 25% holdout was untouched until selection

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.254 | 0.278 |
| MAE | 2529.1 | 2403.5 |
| RMSE | 3760.8 | 3601.7 |
| WAPE | -- | 49.73% |
| sMAPE | -- | 51.32% |
| MAPE | -- | 90.15% |
| MASE (vs. province-mean naive) | -- | 0.814 |
| Bias | -- | 84.7 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = 4.60%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.220 | 2546.5 |
| Cavite | 0.226 | 2759.8 |
| Laguna | 0.330 | 2523.8 |
| Quezon | 0.361 | 1774.5 |
| Rizal | 0.282 | 2829.5 |

## Proxy-mapping caveat

`FRUIT` is a household expenditure-category proxy for **Banana**, not a measurement of physical purchase quantity of that commodity. Treat outputs as directional/indicative demand pressure, not literal commodity volume.

## Verdict

**INDICATIVE_PROXY** -- weak explanatory power; use for relative/directional signal, not precise point forecasts

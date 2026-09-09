# Demand-proxy validation report -- Rice (via BREAD proxy)

Artifact: `demand/rice.joblib` | Target column: `BREAD` | Model selected: **GradientBoostingRegressor**

## Dataset
- Training households: 6117
- Held-out households: 2039
- Provinces covered: Batangas, Cavite, Laguna, Quezon, Rizal

## Candidate comparison (weighted metrics, sample_weight = RFACT)

| Candidate | weighted R2 | weighted MAE | weighted RMSE | normalized MAE % | aggregate bias % |
|---|---|---|---|---|---|
| GradientBoostingRegressor **(selected)** | 0.537 | 6112.0 | 8518.2 | 23.7% | 1.36% |
| XGBRegressor | 0.531 | 6123.3 | 8576.0 | 23.7% | 1.22% |

Tuning note: no additional tuning attempted (candidate already at/above the usable-proxy band)

## Selected model -- full metric set

| Metric | Weighted (survey-representative) | Unweighted (raw holdout) |
|---|---|---|
| R2 | 0.537 | 0.553 |
| MAE | 6112.0 | 6116.5 |
| RMSE | 8518.2 | 8494.4 |
| WAPE | -- | 23.35% |
| sMAPE | -- | 23.95% |
| MAPE | -- | 27.86% |
| MASE (vs. province-mean naive) | -- | 0.651 |
| Bias | -- | 146.7 |

MASE is computed against a **province-mean naive baseline** (predict each held-out household's target as the training-set mean for its province), not a seasonal-lag naive, because FIES 2023 is cross-sectional with no time axis. MASE < 1 means the model beats that province-mean baseline; MASE >= 1 means it does not.

## Population-level bias check

`weighted_aggregate_error_pct` = 1.36%. Formula: `(weighted_mean(prediction, RFACT) - weighted_mean(actual, RFACT)) / weighted_mean(actual, RFACT) * 100`, computed on the holdout set only. This is a population-level bias check -- overestimates and underestimates at the household level can cancel out here -- and is not a substitute for the per-household WAPE/MASE above.

## Province leave-one-out holdout

| Province | R2 | MAE |
|---|---|---|
| Batangas | 0.519 | 6118.0 |
| Cavite | 0.491 | 6666.7 |
| Laguna | 0.471 | 6675.6 |
| Quezon | 0.451 | 6868.9 |
| Rizal | 0.528 | 6622.6 |

## Proxy-mapping caveat

`BREAD` is a household expenditure-category proxy for **Rice**, not a measurement of physical purchase quantity of that commodity. Treat outputs as directional/indicative demand pressure, not literal commodity volume.

## Verdict

**USABLE_PROXY** -- weighted R2 and/or WAPE meet the usable-proxy bar

# Quarterly 101-feature vegetable-expenditure model

The target is raw FIES household-summary `VEG` expenditure. Training uses the recovered
2018 rows plus the non-held-out 2023 split (`test_size=0.20`, `random_state=42`).
`SURVEY_WEIGHT` is used only as XGBoost `sample_weight`; it is not a predictor.

## Dataset

- Features: 101
- Model-training households: 13,877
- Held-out 2023 households: 1,632
- 2018 households: 7,353
- Non-held-out 2023 households: 6,524

## Held-out evaluation

{
  "training_households": 13877,
  "heldout_households": 1632,
  "r2": 0.15352845468577114,
  "mae": 3478.0755960159413,
  "rmse": 5561.29411490121,
  "normalized_mae_percent": 45.22840920623579,
  "aggregate_bias_percent": -8.302415615113318,
  "target_mean": 7690.024161929639,
  "prediction_mean": 7051.566395103606,
  "minimum_prediction": 1780.3416748046875,
  "maximum_prediction": 16919.607421875,
  "negative_predictions": 0,
  "nonfinite_predictions": 0
}

## Quarterly inference

2025 Q3 inference produced 11,174 household vegetable-expenditure
predictions with finite outputs and exact 101-feature alignment. These are household
`VEG` expenditure predictions, not regional vegetable-demand estimates.

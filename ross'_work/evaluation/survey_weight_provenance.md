# Survey-weight provenance

The historical generator copies household-summary `RFACT` into `SURVEY_WEIGHT`; it does not include the weight among the 129 predictors. The recovered cross-year training script passes `SURVEY_WEIGHT` to XGBoost as `sample_weight` for 2018 training, 2023 training, and cross-validation. The BREAD target itself is copied unweighted from the household summary; weights affect model fitting and evaluation rather than altering the stored household target.

The old runtime regional annual estimate computes `sum(prediction * SURVEY_WEIGHT)` in `ml/forecasting/demand_pipeline.py`. Its weighted evaluation also uses `SURVEY_WEIGHT`. Raw standalone quarterly LFS exposes `PUFPWGTPRV`, but that is not the proven historical Model B weight and must not be silently substituted for `RFACT`.

No weight was found in the 129-feature manifest.

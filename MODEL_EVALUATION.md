# Model Evaluation: Vegetable and Fruit Household-Expenditure Models

Scope: this report evaluates the current quarterly-safe 101-feature XGBoost models: `xgboost_vegetable_quarterly_101.json` and `xgboost_fruit_quarterly_101.json`. A separate vegetable-only 129-feature diagnostic artifact exists, but it is not the 101-feature model used for the reported quarterly prediction output and is not evaluated here. No models were retrained.

Unless otherwise stated, test metrics are **survey-weighted** using the project's `SURVEY_WEIGHT` convention. Numbers marked *calculated* were computed read-only from the saved held-out prediction files; the primary R2/MAE/RMSE values also appear in the existing model reports.

## 1. Model Overview

| Item | Vegetable model | Fruit model |
|---|---|---|
| Model name | `xgboost_vegetable_quarterly_101` | `xgboost_fruit_quarterly_101` |
| Target | Raw FIES household-summary `VEG` expenditure | Raw FIES household-summary `FRUIT` expenditure |
| Algorithm | XGBoost `XGBRegressor`, `reg:squarederror` | Same |
| Training data | 2018 prepared table (7,353 rows) + non-held-out 2023 prepared table (6,524 rows) | Same prepared rows; `FRUIT` joined from raw FIES summary |
| Test data | Held-out 2023 prepared households (1,632 rows) | Same held-out 2023 households (1,632 rows) |
| Training samples / test samples | 13,877 / 1,632 | 13,877 / 1,632 |
| Input features | 101 quarterly-safe LFS household features | Same 101 features in identical order |
| Split | `train_test_split(indices, test_size=0.20, random_state=42, shuffle=True)` on 2023; all 2018 rows are added to training | Same |
| Cross-validation | Not found in these training scripts | Not found in these training scripts |
| Weights | `SURVEY_WEIGHT` passed to `model.fit(..., sample_weight=...)` and weighted metrics | Same |
| Parameters | 900 trees; learning rate 0.01; depth 2; min child weight 12; subsample 0.65; colsample 0.50; gamma 0.05; L1 0.50; L2 5; seed 42 | Identical |
| Transformations | No target log transform, scaling, standardization, normalization, clipping, or winsorization in the production 101-feature script | Same |

The full ordered feature list is 101 columns long and is therefore referenced rather than duplicated: `ml/demand/artifacts/xgboost_vegetable_quarterly_101_features.json` and `ml/demand/artifacts/xgboost_fruit_quarterly_101_features.json` (identical manifests). It covers household composition, age, education, labor-force status, work hours, household-head attributes, occupation/class/nature/education shares, and PSIC industry-section shares. It excludes `HOUSEHOLD_ID`, `SURVEY_WEIGHT`, `BREAD`, `VEG`, and `FRUIT`.

Preprocessing creates one FIES-LFS household row by joining FIES household summary information to member-derived LFS aggregates, then filters CALABARZON (`W_REGN == 4`; province codes 10, 21, 34, 56, 58). Member aggregation supplies demographic, employment, education, occupation, industry, worker-class, nature-of-employment, and work-hour features. The fruit/vegetable scripts replace the prepared table's `BREAD` target by a one-to-one raw-FIES join on `SEQUENCE_NO` (2018) or `SEQ_NO` (2023).

## 2. Evaluation Metrics

Main figures below are weighted test metrics unless a row says otherwise. MSE is `RMSE²`. Median quantities are unweighted because the project supplies no weighted-median metric.

| Metric | Vegetable Model | Fruit Model |
|---|---:|---:|
| R2 | 0.1535 | 0.1751 |
| MAE | 3,478.08 | 2,577.46 |
| RMSE | 5,561.29 | 4,099.40 |
| MSE | 30,927,992.20 | 16,805,055.11 |
| MAPE | N/A* (70.40% positive-only) | N/A* (91.85% positive-only) |
| Median AE (unweighted) | 2,365.37 | 1,627.62 |
| Mean actual | 7,690.02 | 4,977.01 |
| Median actual (unweighted) | 5,930.00 | 3,600.00 |
| Std. actual (unweighted) | 5,887.00 | 4,458.12 |
| Mean prediction | 7,051.57 | 4,280.78 |
| Median prediction (unweighted) | 6,846.91 | 3,907.89 |

\* Full-sample MAPE is undefined because the held-out targets contain zero values (VEG: 8; FRUIT: 6). The positive-only values exclude those zeros and are still unstable near zero: the smallest positive actual is 85 pesos for VEG and 16 pesos for FRUIT. They should not be treated as the primary accuracy measure.

## 3. Baseline Comparison

Baselines are constants from the **weighted training target**: its weighted mean and weighted median. They are evaluated with the same held-out weights as the models.

| Target / baseline | R2 | MAE | RMSE | Result |
|---|---:|---:|---:|---|
| Vegetable: model | 0.1535 | 3,478.08 | 5,561.29 | Better than both constants |
| Vegetable: training weighted mean (7,104.62) | -0.0094 | 3,885.59 | 6,072.91 | Worse |
| Vegetable: training weighted median (5,950.00) | -0.0829 | 3,792.02 | 6,290.09 | Worse |
| Fruit: model | 0.1751 | 2,577.46 | 4,099.40 | Better than both constants |
| Fruit: training weighted mean (4,250.93) | -0.0259 | 2,930.16 | 4,571.60 | Worse |
| Fruit: training weighted median (3,075.00) | -0.1776 | 2,946.64 | 4,897.96 | Worse |

Both models meaningfully improve weighted MAE and RMSE over these simple baselines, despite modest R2.

## 4. Error Relative to Target Scale

The primary normalization uses the weighted held-out mean, consistent with the project’s `normalized_mae_percent`: MAE / weighted mean actual. RMSE is normalized by the same denominator. Range-normalized values are supplied only as a supplementary check because each target range is heavily affected by outliers.

| Measure | Vegetable | Fruit |
|---|---:|---:|
| MAE / weighted mean actual | 45.23% | 51.79% |
| RMSE / weighted mean actual | 72.32% | 82.36% |
| MAE / held-out unweighted range | 3.60% | 6.12% |
| RMSE / held-out unweighted range | 5.76% | 9.74% |

The range-based percentages look small because the test ranges include extreme values (96,510 VEG; 42,095 FRUIT); mean-based normalization is more informative here.

## 5. Prediction Diagnostics

Residual = prediction minus actual; residual summaries are unweighted.

| Diagnostic | Vegetable | Fruit |
|---|---:|---:|
| Min / max actual | 0 / 96,510 | 0 / 42,095 |
| Min / max prediction | 1,780.34 / 16,919.61 | 892.33 / 11,697.33 |
| Mean residual | -478.94 | -660.57 |
| Median residual | 668.28 | 312.06 |
| Residual standard deviation | 5,355.86 | 3,962.64 |
| Prediction std. / actual std. | 2,040.95 / 5,887.00 | 1,646.04 / 4,458.12 |
| Negative predictions | 0 | 0 |
| Top 1% target rows’ share of total squared error | 39.65% | 32.67% |

Both prediction distributions are compressed toward the center: their prediction standard deviations are about 35–37% of actual-target standard deviation. Both models underpredict on average (negative mean residual), while their positive median residual shows that a smaller number of large underpredictions pull the average down. High-demand households are the main weakness.

| Held-out target range | Vegetable: actual mean / prediction mean / weighted MAE | Fruit: actual mean / prediction mean / weighted MAE |
|---|---|---|
| Bottom 25% | 2,653.60 / 5,735.09 / 3,287.53 | 1,293.75 / 3,229.03 / 2,036.67 |
| 25–50% | 4,953.73 / 6,660.40 / 2,119.67 | 2,783.80 / 3,786.76 / 1,293.88 |
| 50–75% | 7,343.70 / 7,163.88 / 1,501.95 | 4,674.46 / 4,438.34 / 1,376.95 |
| Top 25% | 14,766.01 / 8,237.31 / 6,609.51 | 10,691.84 / 5,339.08 / 5,374.56 |

The models overpredict the lowest quartile and substantially underpredict the top quartile. Outliers materially affect RMSE: the highest 1% of actual targets accounts for roughly one-third or more of squared error.

## 6. Train vs Test Performance

Weighted metrics. Train metrics were *calculated* by loading each saved model and predicting the already prepared, non-held-out training rows; no fit was performed.

| Metric | Vegetable Train | Vegetable Test | Fruit Train | Fruit Test |
|---|---:|---:|---:|---:|
| R2 | 0.2152 | 0.1535 | 0.2095 | 0.1751 |
| MAE | 3,160.43 | 3,478.08 | 2,393.90 | 2,577.46 |
| RMSE | 4,640.73 | 5,561.29 | 3,741.46 | 4,099.40 |

There is a modest train–test gap, especially for vegetable RMSE, but not the very large gap typical of severe overfitting. The low training R2 as well as low test R2 is consistent with limited signal and/or high household-level target variance; it does not establish a causal explanation.

## 7. Target Distribution

This table uses all 15,509 prepared target rows (2018 + 2023), not only the held-out sample. Statistics are unweighted except the separately noted weighted mean. Skewness is the sample skewness calculated from the held-out target because that is the prediction-evaluation population.

| Statistic | Vegetable (`VEG`) | Fruit (`FRUIT`) |
|---|---:|---:|
| Count | 15,509 | 15,509 |
| Mean / weighted mean | 6,915.09 / 7,166.22 | 4,169.24 / 4,327.33 |
| Median | 5,760.00 | 3,025.00 |
| Standard deviation | 5,167.61 | 4,064.18 |
| Min / Q25 / Q75 / P90 | 0 / 3,684 / 8,763 / 12,725 | 0 / 1,664 / 5,270 / 8,626 |
| P95 / P99 / max | 15,923.60 / 24,811.12 / 140,020 | 11,440.00 / 19,743.80 / 71,398 |
| Zero count / percentage | 101 / 0.651% | 37 / 0.239% |
| Held-out skewness | 4.06 | 2.68 |

Both targets are strongly right-skewed with extreme outliers. They have some zeros, but neither is highly zero-inflated in absolute prevalence; skewness and extreme high values are the larger distributional concern.

## 8. Feature Importance

Importance is normalized XGBoost gain from each saved model’s booster (relative share of total gain); it is associative, not causal.

| Rank | Vegetable feature | Importance |
|---:|---|---:|
| 1 | `WORKING_AGE_MEMBERS` | 6.99% |
| 2 | `MAX_ADULT_EDUCATION_LEVEL` | 5.57% |
| 3 | `EDU_LEVEL_6_SHARE` | 4.81% |
| 4 | `ADULTS_15_64` | 4.15% |
| 5 | `FEMALE_MEMBERS` | 2.98% |
| 6 | `EMPLOYED_MEMBERS` | 2.97% |
| 7 | `MEAN_ADULT_EDUCATION_LEVEL` | 2.87% |
| 8 | `MEMBER_COUNT` | 2.82% |
| 9 | `IND_SECTION_C_SHARE` | 2.74% |
| 10 | `TOTAL_HOUSEHOLD_WORK_HOURS` | 2.51% |

| Rank | Fruit feature | Importance |
|---:|---|---:|
| 1 | `MAX_ADULT_EDUCATION_LEVEL` | 6.90% |
| 2 | `EDU_LEVEL_6_SHARE` | 4.57% |
| 3 | `MEAN_ADULT_EDUCATION_LEVEL` | 4.14% |
| 4 | `OCC_MAJOR_7_SHARE` | 3.21% |
| 5 | `OCC_MAJOR_2_SHARE` | 2.81% |
| 6 | `HEAD_EDUCATION_LEVEL` | 2.75% |
| 7 | `IND_SECTION_C_SHARE` | 2.59% |
| 8 | `IND_SECTION_I_SHARE` | 2.21% |
| 9 | `ADULTS_15_64` | 2.16% |
| 10 | `OCC_MAJOR_4_SHARE` | 1.86% |

## 9. Important Methodological Details

| Check | Finding | Evidence / qualification |
|---|---|---|
| Target in predictors | Does not appear to exist | Scripts explicitly reject target names and `SURVEY_WEIGHT` in the feature list. Manifest check confirms all target names and `HOUSEHOLD_ID` are absent. |
| Household identifier as predictor | Does not appear to exist | `HOUSEHOLD_ID` is used only for one-to-one target attachment and prediction output. |
| Direct geographic identifier as predictor | Does not appear to exist | Province/region are used for CALABARZON filtering; no province/region column appears in the 101-feature manifest. |
| Duplicate train/test 2023 households | Does not appear to exist | Recalculation of the saved split found zero `HOUSEHOLD_ID` intersection between the 6,524 non-held-out and 1,632 held-out 2023 rows. |
| FIES/LFS target join | One-to-one validation present | Both target-attachment functions use pandas `validate="one_to_one"` and reject duplicate raw household IDs or missing/negative targets. |
| Weight handling | Appears consistent with project design | `RFACT` is documented as copied to `SURVEY_WEIGHT`; it is passed as XGBoost `sample_weight` in fitting and in all primary evaluation metrics, never a predictor. |
| Target-derived features | Does not appear to exist in the 101 contract | Contract/provenance describes LFS demographic, labor, education, occupation, industry, and hour features; no food-expenditure fields are present. Absolute proof beyond inspected code is not available. |
| Preprocessing relative to split | Prepared features precede split | The household feature table is already engineered before the train/test split. No fit-dependent scaler/imputer is shown, and target attachment occurs after reading the prepared table; this alone is not evidence of leakage. |
| Test data used for model fitting | Does not appear to exist | Scripts train on 2018 + `train_idx` 2023 only, then predict `test_idx` 2023. |
| Hyperparameter selection against test data | Cannot be determined | No tuning or cross-validation procedure was found in the two current training scripts; the origin of the fixed parameter dictionary is not documented there. |

## 10. Final Assessment

## Vegetable Model

R2: 0.1535  
MAE: 3,478.08 pesos (45.23% of weighted mean actual)  
RMSE: 5,561.29 pesos (72.32% of weighted mean actual)

Interpretation:

- Explains about 15% of weighted held-out variance and improves materially over weighted mean/median baselines.
- Typical absolute error is about 3.5k pesos; RMSE is substantially larger than MAE because high-demand outliers generate large errors.
- The model is biased low in the weighted aggregate (-8.30% in the existing report), overpredicts the lowest quartile, and underpredicts the highest quartile.
- The evidence supports substantial target variance/skewness and limited current feature signal; it does not isolate whether additional model changes would improve performance.

## Fruit Model

R2: 0.1751  
MAE: 2,577.46 pesos (51.79% of weighted mean actual)  
RMSE: 4,099.40 pesos (82.36% of weighted mean actual)

Interpretation:

- Explains about 18% of weighted held-out variance and improves over both simple baselines.
- Typical absolute error is about 2.6k pesos; RMSE substantially exceeds MAE due to large high-target errors.
- The model is biased low in the weighted aggregate (-13.99% in the existing report), with especially large top-quartile underprediction.
- The low R2 is consistent with a skewed, variable household target and limited current predictors; a specific causal source cannot be determined from evaluation alone.

# Overall Comparison

Fruit has the higher held-out R2 (0.1751 vs 0.1535) and lower absolute MAE/RMSE, while vegetable has slightly lower error relative to its weighted mean target. Both models beat constant baselines but show the same central failure mode: compressed predictions and underprediction of high-expenditure households.

# Files Inspected

- Training/evaluation code: `ml/demand/pipeline/train_vegetable_101.py`, `ml/demand/pipeline/train_fruit_101.py`, `ml/demand/pipeline/train_quarterly_101.py`.
- Preprocessing/provenance: `ml/demand/pipeline/provenance_recovery.py`, `ml/demand/pipeline/quarterly_lfs_feature_builder.py`, `data/processed/demand/evaluation/training_provenance_audit.md`, `data/processed/demand/evaluation/survey_weight_provenance.md`.
- Saved models/manifests/parameters: `ml/demand/artifacts/xgboost_vegetable_quarterly_101.json`, `ml/demand/artifacts/xgboost_fruit_quarterly_101.json`, and their `_features.json` / `_parameters.json` companions.
- Saved evaluation outputs: `data/processed/demand/evaluation/vegetable_101_model_report.md`, `data/processed/demand/evaluation/fruit_101_model_report.md`, `data/processed/demand/evaluation/vegetable_101_heldout_predictions.csv`, `data/processed/demand/evaluation/fruit_101_heldout_predictions.csv`.
- Training data/contract/raw target sources: `data/processed/demand/fies_lfs/fies_lfs_2018_harmonized_psic_training_table.csv`, `data/processed/demand/fies_lfs/fies_lfs_2023_training_table.csv`, `data/processed/demand/evaluation/validated_quarterly_lfs_feature_contract.csv`, `data/raw/PHL-PSA-FIES-LFS/FIES-LFS-houseHoldSummary.CSV`, and `data/raw/PHL-PSA-FIES-LFS/PHL-PSA-FIES-LFS-2018-PUF/FIES-LFS PUF 2018 Household Summary.CSV`.
- Supporting existing diagnostics: `data/processed/demand/diagnostics/target_distribution_comparison.csv` and `data/processed/demand/diagnostics/target_diagnostic_model_comparison.csv`.
- Notebooks: no `.ipynb` files were found in the workspace search.

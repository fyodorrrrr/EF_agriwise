# Isolated AgriWise Demand Pipeline Workspace

This folder is a self-contained working copy for the FIES-LFS / XGBoost demand pipeline. Existing project files outside `ross'_work/` were not moved, renamed, deleted, or modified.

## Current implementation verdict

The proportional Denton and spatial reconciliation stages are implemented and tested here. Model B artifact/manifest validation is implemented. The current quarterly LFS table is **not compatible** with Model B inference, so this workspace intentionally fails before XGBoost inference instead of fabricating the missing features.

The available quarterly LFS table has seven regional fields:

```text
YEAR, QUARTER, MONTH, REGION,
UNEMPLOYMENT_RATE, LFPR, AVG_TOTAL_HOURS_WORKED
```

Model B requires 129 household-level features. No mathematically justified transformation from those seven regional aggregates into the 129 household-level features was found in the current repository. A retraining or feature-engineering decision is therefore required before a legitimate current-quarter XGBoost run can be produced.

## Intended methodology implemented in this workspace

```text
Quarterly LFS
    |
    v
Feature harmonization / exact Model B contract validation
    |
    v
XGBoost Model B
    |
    v
Quarterly demand indicator
    |
    v
Proportional Denton
    |
    v
Regional quarterly benchmark-consistent estimate
    |
    v
2023 FIES spatial reconciliation
    |
    v
Province quarterly estimate
```

The mathematical target is:

```text
p_t = f_theta(X_t^LFS)

Y_t = Denton(p_1:T, B)_t

Y_(t,r) = w_r * Y_t
```

where `p_t` is the raw XGBoost indicator, `B` is an explicitly supplied annual benchmark, and `w_r` is a fixed 2023 FIES spatial share. The implementation does not Denton-adjust predictors and does not apply spatial weights before XGBoost.

## Files copied

| Workspace file | Original path | Type | Purpose | Used by new runtime? |
|---|---|---|---|---|
| `data/lfs/lfs_calabarzon_quarterly_features.csv` | `data/processed/FIES-LFS/lfs_calabarzon_quarterly_features.csv` | Inference data | Seven-column regional quarterly LFS feature table, covering 2021–2025 with gaps | Yes, as the validated input that currently fails closed at the Model B boundary |
| `data/lfs/lfs_calabarzon_combined.csv` | `data/processed/FIES-LFS/lfs_calabarzon_combined.csv` | Source/inference data | Combined LFS records used by the existing offline preparation | No direct runtime reader; retained for provenance |
| `data/fies_lfs/fies_lfs_2018_2023_harmonized_psic_training_table.csv` | `data/processed/training/fies_lfs_2018_2023_harmonized_psic_training_table.csv` | Training data | Combined 2018 + 2023 household training table associated with Model B | No direct runtime reader; retained for training provenance |
| `data/fies_lfs/fies_lfs_2023_training_table.csv` | `data/processed/training/fies_lfs_2023_training_table.csv` | Inference/training data | Existing 2023 household table used by the old Model B runtime | No direct reader in the new fail-closed quarterly path |
| `models/xgboost_model_b_2018_2023.json` | `data/processed/training/psic_model_2digit_harmonized/xgboost_model_b_2018_2023.json` | Model artifact | Saved XGBoost Model B booster | Intended by runtime; binary loading requires the XGBoost package |
| `models/xgboost_model_features.json` | `data/processed/training/psic_model_2digit_harmonized/xgboost_model_features.json` | Model artifact | Exact saved feature order; 129 features | Yes, for contract validation |
| `models/xgboost_parameters.json` | `data/processed/training/psic_model_2digit_harmonized/xgboost_parameters.json` | Model metadata | Saved training hyperparameters | Retained for audit; not required for inference |
| `models/xgboost_heldout_2023_predictions.csv` | `data/processed/training/psic_model_2digit_harmonized/xgboost_heldout_2023_predictions.csv` | Evaluation data | Household held-out Model A/Model B predictions for 2023 | Retained for evaluation; not used to generate forecasts |
| `data/benchmarking/fies_2023_calabarzon_spatial_benchmark.csv` | `data/processed/benchmarking/fies_2023_calabarzon_spatial_benchmark.csv` | Benchmark data | 2023 FIES-derived province spatial shares | Yes, by spatial reconciliation when a regional Denton result exists |
| `data/benchmarking/fies_lfs_calabarzon_temporal_benchmark.csv` | `data/processed/benchmarking/fies_lfs_calabarzon_temporal_benchmark.csv` | Benchmark data | Existing 2023 quarter benchmark and fixed shares | No; fixed quarter shares are not used by the new Denton module |
| `pipeline/denton.py` | New/updated | Code | Proportional Denton implementation with explicit benchmark metadata and provenance preservation | Yes |
| `pipeline/indicator_projection.py` | New | Code | Completes missing future quarters with explicit forecast indicators or a labeled development baseline | Yes |
| `pipeline/current_year.py` | New | Code | Current-year orchestration: projection completion, Denton, then spatial reconciliation | Yes |
| `pipeline/inference.py` | New | Code | Model B manifest validation and guarded XGBoost inference boundary | Yes |
| `pipeline/spatial.py` | New | Code | Fixed base-year FIES spatial validation and reconciliation | Yes |
| `pipeline/run_pipeline.py` | New | Code | Pipeline orchestration entrypoint | Yes, but current source stops at the incompatibility |
| `pipeline/__init__.py` | New | Code | Pipeline exports | Yes |
| `tests/test_pipeline.py` | New | Tests | Contract, Denton, spatial, and fail-closed tests | Yes |

No helper module outside these files was required by the isolated pipeline. The old `ml/forecasting/demand_pipeline.py` and `demand_evaluation.py` were inspected but not copied as runtime dependencies because the new methodology deliberately replaces their fixed temporal allocation logic.

## Model B feature contract

The saved manifest contains 129 numeric household-level features, including household composition, labor-force counts and ratios, work hours, occupation/class/nature/pay-basis shares, industry shares, head-of-household fields, and pay-basis-specific pay aggregates.

The manifest does not contain `BREAD`, which is correct because `BREAD` is the target. The new inference boundary requires every manifest feature to be present, numeric, finite, and passed to XGBoost in the saved order. It does not silently fill missing columns.

The current quarterly LFS table cannot satisfy this contract. It is regional and has no household rows, household composition, occupations, industries, pay-basis distributions, or equivalent training-time feature representation.

## Proportional Denton implementation

`pipeline/denton.py` defines:

```python
proportional_denton(indicators, benchmarks)
```

It defines `z_t = Y_t / p_t` and solves the constrained least-squares problem:

```text
minimize sum((z_t - z_(t-1))²)
subject to sum(Y_t in year a) = B_a
where Y_t = p_t * z_t
```

The ratio movement is the objective being minimized; it is not treated as an equality constraint. The function rejects non-finite, non-positive, duplicate, missing, or incomplete quarterly indicators. It also requires an explicit annual benchmark for every included year with:

- `benchmark_value`
- `benchmark_year`
- `benchmark_source`
- `benchmark_status`: `observed`, `estimated`, `forecast`, or `provisional`

No current or future annual benchmark is fabricated.

## Spatial reconciliation

`pipeline/spatial.py` uses the existing `SPATIAL_SHARE` values as:

> 2023 FIES base-year spatial demand shares

It validates non-negativity, finiteness, duplicate provinces, expected province coverage, and sum-to-one. It then computes:

```text
province_quarterly_demand = spatial_share * regional_quarterly_demand
```

The copied spatial file derives its shares from weighted observed 2023 `BREAD` expenditure. This is documented as a fixed structural base-year allocation, not current-year observed provincial demand.

## Old pipeline versus new isolated pipeline

### Old runtime

```text
2023 household FIES-LFS table
    -> Model B household predictions
    -> survey-weighted regional annual estimate
    -> fixed 2023 target-derived spatial shares
    -> fixed 2023 quarter shares
```

The old implementation is in `ml/forecasting/demand_pipeline.py`. It reads only `QUARTER_SHARE_PERCENT` from the temporal file and does not directly consume the latest quarterly LFS feature table during XGBoost inference.

### New isolated runtime

```text
quarterly LFS representation
    -> exact Model B feature-contract validation
    -> XGBoost raw quarterly indicator
    -> proportional Denton with explicit annual benchmark
    -> 2023 FIES base-year spatial reconciliation
    -> province quarterly estimate
```

The current source stops before the XGBoost step because the available quarterly representation is incompatible. This is intentional and is a validation result, not a completed forecast.

## Outputs

The runtime is designed to write:

```text
outputs/raw_xgb_quarterly_indicators.csv
outputs/denton_quarterly_estimates.csv
outputs/province_quarterly_estimates.csv
```

The output units are Model B `BREAD` expenditure units, not metric tons. Any later conversion using price must be a separate, explicit transformation.

No forecast output files were generated from the current seven-column LFS table because doing so would require inventing 122 missing Model B features. No annual benchmark was supplied for a current year either.

## Validation performed

The copied files were inspected from inside this workspace:

- Model JSON file exists and is readable as an artifact file.
- Feature manifest loads successfully and contains 129 features.
- 2023 household training table loads successfully.
- Quarterly LFS table loads successfully.
- Spatial and temporal benchmark CSVs load successfully.
- Spatial shares sum to 1 and cover five provinces.
- Temporal benchmark shares sum to 100% per province, but contain only 2023 Q1–Q4.
- Existing temporal `QUARTERLY_ESTIMATE` values reconcile to annual benchmark times quarter share.
- The quarterly LFS schema cannot satisfy the Model B feature manifest.

Tests:

```text
16 passed
```

The tests cover exact feature-manifest checks, refusal to fabricate LFS-to-Model-B features, complete and incomplete current-year indicator workflows, Denton annual additivity, explicit benchmark requirements, forecast provenance, as-of safety, and spatial additivity. Loading the XGBoost booster itself additionally requires the declared `xgboost==3.4.1` package; the current environment did not have that package installed.

## Run commands

From the repository root:

```powershell
$work = Join-Path (Get-Location) "ross'_work"
$env:PYTHONPATH = $work
pytest "$work/tests" -q
python -m pipeline.run_pipeline
```

The current `run_pipeline` command is expected to stop with a clear feature-contract error. That is the correct behavior until a valid 129-feature quarterly inference table or a separately approved retraining design is supplied.

## Example trace

For a valid future quarterly feature row, the intended trace is:

```text
LFS quarter t
  -> ModelBInference.align_features()
  -> XGBoost Model B predicts p_t
  -> proportional_denton([p_1, ..., p_T], explicit annual B)
  -> regional benchmark-consistent Y_t
  -> reconcile_spatial(Y_t, 2023 FIES spatial shares)
  -> province r receives w_r * Y_t
```

For the current repository's latest available LFS row, the trace stops at `align_features()` because the seven regional columns do not contain the 129 household-level Model B features.

## Open methodological decisions

Before producing a current-quarter forecast, one of the following must be resolved:

1. Produce quarterly inference rows using the same 129-feature engineering used at training time, with a defensible mapping from current LFS data to household-level features; or
2. Retrain a model whose training features are the seven quarterly regional LFS features; or
3. Supply another approved quarterly feature source that matches the existing Model B semantic contract.

None of these choices should be made silently. The current implementation intentionally does not select one.

## Incomplete-year workflow

The complete-year requirement has not been removed. Instead, missing future quarters are completed before Denton.

For a Q3 as-of forecast, the required input is:

```text
2026 Q1  p_Q1       model_derived
2026 Q2  p_Q2       model_derived
2026 Q3  p_Q3       model_derived
2026 Q4  p_hat_Q4   forecast
```

The complete vector is then passed to Denton:

```text
[p_Q1, p_Q2, p_Q3, p_hat_Q4]
        |
        v
proportional Denton with annual benchmark B_2026
        |
        v
[Y_Q1, Y_Q2, Y_Q3, Y_Q4]
```

The annual restriction remains:

```text
Y_Q1 + Y_Q2 + Y_Q3 + Y_Q4 = B_2026
```

The pipeline never imposes `Y_Q1 + Y_Q2 + Y_Q3 = B_2026`.

### Indicator provenance schema

Every indicator row now requires:

| Column | Meaning |
|---|---|
| `year` | Indicator year |
| `quarter` | Quarter 1–4 |
| `raw_xgb_indicator` | Positive raw indicator before Denton |
| `indicator_status` | `observed`, `model_derived`, `forecast`, or `provisional` |
| `indicator_source` | Source or projection method |
| `as_of_date` | Information cutoff date |

The Denton output preserves these fields and adds `annual_benchmark`, `benchmark_source`, and `benchmark_status`. This makes it visible that a Q3 estimate depends on a forecast Q4 indicator.

### `pipeline/indicator_projection.py`

`project_missing_quarters()` is the separate future-indicator stage. It does not perform benchmarking.

Its default method is `explicit`. Under this method, the caller must supply every missing future quarter as a row marked `indicator_status="forecast"`. The function rejects:

- missing future projections;
- projection rows for quarters that already exist;
- forecast rows at or before the current quarter;
- future rows incorrectly marked observed/model-derived/provisional;
- duplicate quarters;
- zero, negative, NaN, or infinite indicators;
- incomplete years after projection completion.

The module also contains `carry_forward_baseline`. This is explicitly labeled `carry_forward_baseline_development_only`, requires an `as_of_date`, and repeats the latest available current-year indicator into missing future quarters. It exists for development tests only and is not selected by default or claimed as the validated forecasting method.

### `pipeline/current_year.py`

`run_current_year_pipeline()` is the intended current-year entrypoint:

```python
run_current_year_pipeline(
    observed_indicator_rows,
    annual_benchmark,
    spatial_weights,
    current_quarter=3,
    projected_indicator_rows=projected_q4,
)
```

Execution order is fixed:

1. Validate and combine observed and forecast indicators.
2. Require exactly Q1–Q4.
3. Run proportional Denton with the explicit annual benchmark.
4. Reconcile the benchmarked regional result spatially.
5. Optionally write the raw, Denton, and province output CSVs.

If projections are not supplied for an incomplete year, it raises `IncompleteYearError` with a message explaining that annual Denton cannot be imposed yet. Denton itself never invents missing quarters.

### Example Q3 trace

```text
Inputs as of 2026-09-30:

Q1: 10250, model_derived, XGBoost
Q2: 10820, model_derived, XGBoost
Q3: 11540, model_derived, XGBoost
Q4: 11200, forecast, explicit_future_indicator_model

        |
        v

Denton([10250, 10820, 11540, 11200], B_2026)

        |
        v

Y_Q1 + Y_Q2 + Y_Q3 + Y_Q4 = B_2026

        |
        v

Return Y_Q3 as:
"2026 Q3 benchmark-consistent demand estimate based on indicators observed or
model-derived through Q3 and a projected Q4 indicator."
```

This example does not use actual Q4 LFS information. Q4 is explicitly a forecast input. The current workspace does not generate this example from Model B because the separate 129-feature incompatibility remains unresolved; the test suite uses synthetic valid indicator rows to validate the temporal architecture.

## Detailed file-by-file code guide

### `pipeline/__init__.py`

This is the package export file. It exposes the public isolated-pipeline objects:

- `ModelBInference`
- `FeatureContractError`
- `proportional_denton`
- `BenchmarkMetadata`
- `DentonError`
- `reconcile_spatial`
- `SpatialError`

It contains no model logic and no data loading side effects.

### `pipeline/inference.py`

This module is the boundary between tabular data and Model B.

`ModelBInference.__init__()`:

1. Resolves the copied model path and feature-manifest path.
2. Verifies both files exist.
3. Loads the JSON feature manifest.
4. Verifies the manifest is a non-empty list of strings.

`align_features(frame)`:

1. Calculates the missing feature names using the saved manifest.
2. Rejects a manifest that contains `BREAD`.
3. Selects columns in the exact saved manifest order.
4. Converts values to numeric values.
5. Rejects NaN and infinite values.
6. Returns the aligned feature table.

`predict(feature_rows)`:

1. Calls `align_features()`.
2. Imports XGBoost.
3. Loads the native JSON booster with `xgb.Booster().load_model()`.
4. Creates an XGBoost `DMatrix` with the exact feature names.
5. Returns non-negative finite predictions.

`predict_from_quarterly_lfs(quarterly_lfs)` is deliberately conservative. It attempts the same contract check against the quarterly LFS table and raises `FeatureContractError` when the table is incompatible. It does not aggregate, broadcast, impute, scale, or rename regional LFS variables into household features.

### `pipeline/denton.py`

This module contains no XGBoost logic and no spatial logic. It only transforms a valid positive indicator series into benchmark-consistent quarterly values.

`BenchmarkMetadata` carries provenance for an annual total. A numeric value alone is not accepted because the pipeline must distinguish observed, estimated, forecast, and provisional benchmarks.

`proportional_denton()` requires a table with:

```text
year
quarter
raw_xgb_indicator
```

It requires exactly four quarters per year, unique year-quarter pairs, positive finite indicators, and one explicit benchmark metadata object per year.

The implementation constructs a first-difference matrix `D` and solves the constrained system in ratio space:

```text
z_t = Y_t / p_t

minimize ||D z||²
subject to A z = B

Y_t = p_t z_t
```

The annual constraint matrix uses the raw indicator values so that each annual constraint is equivalent to:

```text
sum(Y_t for year a) = benchmark_value_a
```

The implementation uses a KKT least-squares solve, then checks finiteness, non-negativity, and annual additivity. It rejects zero or near-zero indicators because proportional Denton requires division by the indicator. It also rejects incomplete years rather than silently inventing missing quarters.

### `pipeline/spatial.py`

`validate_spatial_weights()` normalizes the copied spatial table to internal columns:

```text
province
spatial_share
```

It checks:

- required columns exist;
- provinces are unique;
- shares are numeric and finite;
- shares are non-negative;
- shares sum to one within tolerance;
- optional expected province sets match exactly.

`reconcile_spatial()` accepts regional quarterly estimates with `year`, `quarter`, and `benchmarked_quarterly_demand`. It performs a Cartesian pairing of every regional quarter with every province weight, computes the province estimate, and verifies that the province total equals the regional total for every quarter.

### `pipeline/run_pipeline.py`

This is the orchestration boundary.

`run_from_valid_model_rows()` is the successful-path function. It expects a table containing:

- `year`;
- `quarter`;
- all 129 Model B features.

It then performs:

1. Model B inference;
2. raw indicator output creation;
3. proportional Denton using caller-supplied annual benchmark metadata;
4. spatial reconciliation using the copied 2023 FIES shares;
5. writing of the three output CSVs.

The module-level `run()` is the current-data diagnostic path. It reads the copied seven-column quarterly LFS table, sends it through the guarded inference boundary, and stops with a detailed incompatibility error. This is expected until a valid quarterly Model B feature table exists.

## Data schemas and semantics

### Quarterly LFS feature table

`data/lfs/lfs_calabarzon_quarterly_features.csv` contains 18 rows and these columns:

| Column | Meaning in current file | Model B status |
|---|---|---|
| `YEAR` | Calendar year | Metadata only |
| `QUARTER` | Quarter number | Metadata only |
| `MONTH` | Source month associated with the quarter | Metadata only |
| `REGION` | Regional identifier | Metadata only |
| `UNEMPLOYMENT_RATE` | Regional unemployment rate | Not a Model B feature |
| `LFPR` | Regional labor-force participation rate | Not a Model B feature |
| `AVG_TOTAL_HOURS_WORKED` | Regional average hours worked | Not a Model B feature |

The file is a regional time series, not a household feature table. It cannot produce fields such as `MEMBER_COUNT`, `HEAD_AGE`, occupation shares, industry shares, or pay-basis means without an approved model and data-generation method.

### Model B feature manifest

The 129 features are household-level variables grouped broadly as:

- household composition: member counts, sex shares, age groups, dependency;
- household head: age, education, employment, hours, pay;
- labor status: labor-force, employed, unemployed, and not-in-labor-force counts;
- labor ratios: employment, unemployment, participation, and working-age shares;
- work intensity: hours per member, total hours, primary-job hours, normal hours;
- categorical distributions: occupation, class, nature, pay-basis, and education shares;
- industry section shares;
- pay-basis-specific average basic pay variables.

These are not interchangeable with the three regional LFS rates in the quarterly feature file.

### Spatial benchmark

The spatial file contains five CALABARZON provinces and columns including:

```text
YEAR
PROVINCE_CODE
PROVINCE
SAMPLE_HOUSEHOLDS
ESTIMATED_HOUSEHOLDS
WEIGHTED_CONSUMPTION
SPATIAL_SHARE
SPATIAL_PERCENT
```

`SPATIAL_SHARE` is numerically equal to each province's weighted 2023 `BREAD` consumption divided by the CALABARZON total. It is therefore target-derived historical structure, not a current observation.

### Existing temporal benchmark

The copied temporal file contains:

```text
YEAR
QUARTER
PROVINCE_CODE
PROVINCE
TEMPORAL_INDEX
QUARTERLY_ESTIMATE
ANNUAL_FIES_BENCHMARK
QUARTER_SHARE_PERCENT
```

It contains only 2023 Q1–Q4 for each province. The old pipeline uses `QUARTER_SHARE_PERCENT`. The new pipeline intentionally does not use it. The new pipeline requires a raw indicator series and an explicit annual benchmark passed to Denton.

## What “current quarter” would require

A defensible current-quarter pipeline needs all of the following:

1. A quarterly data source available by the forecast date.
2. A transformation producing the same semantic unit as the Model B training rows.
3. All 129 Model B features, or an explicitly approved replacement model.
4. A rule for constructing the raw indicator history through the forecast quarter.
5. An annual benchmark that is actually available by the forecast date, or an independently produced estimate clearly marked as estimated/forecast/provisional.
6. A temporal validation design that does not use future LFS values or future FIES targets.
7. A later-observed target for evaluating the complete provincial quarterly output.

The current files provide the LFS time series and the base-year spatial weights, but they do not provide item 2 or item 3 for the existing Model B, and they do not provide a current observed annual benchmark.

## Validation layers

These are separate questions and must not be conflated:

### A. Model validation

Does Model B predict household `BREAD` expenditure accurately on held-out households? The copied held-out file supports this question.

### B. Feature-contract validation

Can the intended inference source produce the same 129 features in the same semantic form as training? The current quarterly LFS file fails this question.

### C. Temporal benchmarking validation

Given a valid positive indicator and a legitimate annual benchmark, does Denton preserve movement while satisfying annual totals? The isolated Denton tests support the arithmetic and constraint behavior.

### D. Spatial reconciliation validation

Do fixed base-year shares sum to one and preserve every regional quarterly total? The isolated spatial tests support this.

### E. End-to-end forecast validation

Does the final province-quarter estimate predict a later-observed province-quarter target under a historical information set? This has not been performed because the current quarterly LFS table cannot feed Model B and no approved quarterly target series is available in this workspace.

Household-level Model B R² and MAE must not be reported as end-to-end quarterly forecast accuracy.

## Failure behavior and safety rules

The isolated runtime intentionally fails in these situations:

- missing Model B features;
- `BREAD` included as a predictor;
- nonnumeric or non-finite features;
- missing XGBoost dependency;
- negative or non-finite predictions;
- missing annual benchmark metadata;
- zero or near-zero Denton indicators;
- incomplete or duplicate quarters;
- invalid spatial weights;
- duplicate provinces;
- provincial totals that do not reconcile to regional totals.

These failures are preferable to producing a number whose statistical meaning is unknown.

## How another AI assistant should interpret this folder

Use the following rules when answering questions about this workspace:

1. Treat `ross'_work/` as isolated from the main AgriWise runtime.
2. Treat copied CSVs as evidence of available data, not evidence that the new code consumes them.
3. Trace actual readers in `pipeline/` before claiming a file is used.
4. Treat Model B's 129-feature manifest as authoritative for inference.
5. Do not invent a mapping from regional LFS aggregates to household features.
6. Treat `BREAD` as expenditure, not physical quantity.
7. Treat the spatial shares as fixed 2023 FIES base-year shares.
8. Treat annual benchmark status as part of the data, not as a cosmetic label.
9. Do not call the current implementation a complete current-quarter forecast.
10. If proposing changes, separate feature-engineering/retraining decisions from the Denton and spatial mathematics already implemented.

## Suggested questions for future review

- Can the existing raw LFS files reproduce the 129 Model B features without using future information?
- Was Model B trained using household-level FIES-LFS rows, regional LFS aggregates, or both?
- What is the correct statistical target for a quarterly demand indicator?
- What independent annual benchmark is available for the current year?
- Should Model B be retained, or should a new model be trained on the seven quarterly regional LFS variables?
- What observed quarterly provincial target can support end-to-end backtesting?
- How should missing LFS quarters be handled without interpolation leakage?
- Should spatial weights remain fixed or be estimated dynamically from a separate non-target source?

## Model B Quarterly LFS Feature Reproducibility Audit

The strict audit is recorded in [`evaluation/model_b_lfs_feature_compatibility.csv`](evaluation/model_b_lfs_feature_compatibility.csv). It contains exactly one row for each of the 129 features in [`models/xgboost_model_features.json`](models/xgboost_model_features.json). The generator is [`pipeline/feature_audit.py`](pipeline/feature_audit.py), and the narrative result is [`evaluation/model_b_lfs_feature_audit.md`](evaluation/model_b_lfs_feature_audit.md).

### Result

| Classification | Count |
|---|---:|
| Directly reproducible (A) | 0 |
| Derivable from raw LFS (B) | 21 |
| Reproducible with existing mapping/codebook (C) | 75 |
| Possibly reproducible; needs verification (D) | 10 |
| Not reproducible from quarterly LFS (E) | 23 |
| Leakage/invalid for current inference (F) | 0 |
| **Total** | **129** |

Using the requested category arithmetic, strictly reproducible is **96/129 (74.42%)** and potentially reproducible is **106/129 (82.17%)**. These are information-availability counts. They are not permission to run the existing model: the original training feature-engineering script was not found in this repository, so the 75 category-C formulas are not verified as training-equivalent. A conservative “formula visibly verified from available artifacts” count is only the 21 simple category-B aggregations.

The 23 unavailable features are the pay block: `BASIC_PAY_REPORTED_WORKERS`, `BASIC_PAY_REPORTED_SHARE`, `HEAD_BASIC_PAY`, ten `PAY_BASIS_*_SHARE` features, and ten `PAY_BASIS_*_MEAN_BASIC_PAY` features. These fields exist in full-format LFS files but are absent from short-format files used in material portions of the available quarterly coverage, including 2022 Q1 and 2025 Q3. Therefore they are not generally reproducible for every quarterly inference period without an explicit, defensible quarter-source rule and additional data.

### Statistical unit audit

The training table is household-level: it has one row per `HOUSEHOLD_ID` and household aggregates such as `MEMBER_COUNT`; `BREAD` is the household target. Raw quarterly LFS is person/member-level, but contains `PUFHHNUM`, a household identifier, so it can in principle be grouped into household inference rows. The LFS household IDs are survey identifiers and are not longitudinal links to FIES household IDs.

Raw LFS files contain demographic, labor-status, hours, occupation, industry, nature-of-employment, class-of-worker, education, and survey-weight fields. The 2023 monthly DCF codebooks provide mappings for these fields. However, raw schemas change between full and short formats and between years. The repository has no raw 2018 quarterly LFS microdata, despite the model's harmonized 2018–2023 training table.

### Source and leakage findings

The final engineered feature names do not appear as raw LFS columns; most must be household aggregations. No manifest feature is `BREAD`, and no FIES-only predictor or future-quarter dependency was identified. Survey weight is not one of the 129 XGBoost predictors; whether it was used only for aggregation/evaluation or also during original feature creation cannot be established because the original preprocessing code is absent. The audit therefore labels feature provenance as “LFS-derived likely; training provenance unverified,” rather than claiming the source lineage is proven.

Feature-family totals are in [`evaluation/model_b_lfs_feature_group_summary.csv`](evaluation/model_b_lfs_feature_group_summary.csv). The largest structural risks are pay/basis availability, the missing original formulas for coded shares and labor definitions, and cross-year schema harmonization. Household IDs are available; the main unit blocker is not grouping but proving that the grouping and denominators match training.

### Recommendation

The answer is **D — UNDETERMINED** for retaining Model B without retraining. Raw quarterly LFS contains substantial candidate information, so the old conclusion “the seven-column summary cannot feed 129 features” is not sufficient. But exact training-equivalent transformations, short/full-format harmonization, quarter selection, and 2018 comparability are not established. The existing Model B must not be used for quarterly inference until those contracts are recovered or independently validated. No model, Denton code, spatial reconciliation, or main runtime was changed by this audit.

The audit also writes [`evaluation/model_b_lfs_feature_source_summary.csv`](evaluation/model_b_lfs_feature_source_summary.csv). A recommended retraining subset was not generated because the evidence-based recommendation is undetermined rather than a definitive “retrain” decision.

## Empirical Quarterly LFS Feature Reconstruction Validation

The final reconstruction audit is documented in [`evaluation/feature_reconstruction_report.md`](evaluation/feature_reconstruction_report.md). The feature-level results are in [`evaluation/feature_reconstruction_validation.csv`](evaluation/feature_reconstruction_validation.csv), with quarterly schema checks in [`evaluation/feature_quarterly_availability.csv`](evaluation/feature_quarterly_availability.csv).

The audit attempted to group raw 2023 LFS person rows by `PUFHHNUM` and compare household features with the 2023 training table. The training table uses `HOUSEHOLD_ID`. Although numeric values overlap across the raw monthly files, the overlap is not a valid join: the training table has no trusted raw-LFS month/province/composite linkage, and overlapping January numeric IDs produce materially different member counts. Consequently, the audit reports **0 trusted matched households** and leaves comparison metrics blank instead of treating numeric coincidence as household identity.

Before Git-history recovery, the empirical audit could not establish a defensible join or locate the original preprocessing code, so it conservatively validated **0 features**. That preliminary result is superseded for the FIES-LFS training pipeline by the forensic recovery documented below. The quarterly standalone-LFS contract remains a separate question.

Raw LFS does contain `PUFHHNUM`, member demographics, labor fields, hours, coded occupation/industry/class/nature/education fields, and `PUFPWGTPRV`. However, that is evidence of possible raw information, not proof that the historical household feature semantics can be recovered. The future regional indicator should only use `p_t = sum_h(w_{h,t} * y_hat_{h,t})` after the training target definition and the role of the LFS weight are recovered. The weight audit is in [`evaluation/survey_weight_audit.md`](evaluation/survey_weight_audit.md); it does not invent a conversion from person weights to household weights.

The preliminary audit did not locate raw 2018 source files on the checked-out tree. The later forensic recovery found the raw 2018 FIES-LFS files locally and recovered the harmonization script from unreachable Git history; see the provenance section below for the superseding result.

## Forensic Training-Provenance Recovery

The later forensic investigation recovered the previously missing historical scripts from unreachable Git history, commit `a733c6293dc75c5e7c64d0b17b3568085cf2a2cf` (`quarterly predictions`). This is inspection evidence; Git history was not restored or modified.

The decisive provenance facts are:

- `HOUSEHOLD_ID` is exactly `SEQ_NO` in the 2023 FIES-LFS household summary and member files.
- The member table is grouped by `SEQ_NO`, renamed to `HOUSEHOLD_ID`, and merged to the household summary with `validate="one_to_one"`.
- The table is filtered to `W_REGN == 4` and province codes 10, 21, 34, 56, and 58.
- `RFACT` becomes `SURVEY_WEIGHT`; `BREAD` is copied as the household target.
- This is not a join to standalone quarterly LFS `PUFHHNUM`. `PUFHHNUM` belongs to the separate LFS PUF files used for quarterly inference.

The recovered generator was executed against the raw local FIES-LFS 2023 files in an isolated output path. It produced 8,156 rows and 136 columns, matching the copied 2023 training table at a 100% per-column exact-match rate. It also recovered 7,353 2018 harmonized rows from the raw 2018 FIES-LFS files; the minimum comparison rate against the current combined table's 2018 block was 100%.

All 129 Model B formulas are now marked `VERIFIED_FROM_CODE` in [`evaluation/feature_engineering_provenance.csv`](evaluation/feature_engineering_provenance.csv). The formula details include the exact denominators: employment ratio uses employed / age-15-plus members; unemployment ratio uses unemployed / labor force; education shares use age-15-plus members; occupation, industry, class, nature, and pay shares use employed members; and distinct occupation/industry counts use harmonized two-digit groups.

Survey-weight provenance is documented in [`evaluation/survey_weight_provenance.md`](evaluation/survey_weight_provenance.md). The recovered cross-year XGBoost script uses `SURVEY_WEIGHT` as `sample_weight`, while the old regional aggregation multiplies predictions by `SURVEY_WEIGHT`. The weight is not one of the 129 predictors.

See the complete report at [`evaluation/training_provenance_audit.md`](evaluation/training_provenance_audit.md), the identifier report at [`evaluation/household_id_provenance.md`](evaluation/household_id_provenance.md), the regeneration comparison at [`evaluation/training_table_regeneration_comparison.csv`](evaluation/training_table_regeneration_comparison.csv), and household-level linkage checks at [`evaluation/household_link_validation.csv`](evaluation/household_link_validation.csv).

## Definitive Standalone Quarterly LFS Reconstruction Audit

The definitive audit applies the recovered feature formulas to new standalone LFS samples. It does not join `PUFHHNUM` to historical `SEQ_NO`: quarterly inference requires the same household unit and feature semantics, not the same sampled households.

The builder grouped member rows by `PUFHHNUM` and produced one household row for four representative periods: 2022 Q1, 2023 Q1, 2024 Q1, and 2025 Q3. All four outputs have unique household rows, no `BREAD` column, exactly the 129 manifest features, zero missing manifest columns, zero missing or multiple household heads, and labor-ratio identity errors below `1.2e-16`. The distribution check found no automatic tenfold scale/unit flags.

The corrected quarterly contract contains 101 features validated with explicit full/short-schema harmonization and 28 period-limited features, for **101/129 = 78.29%**. The 24 pay-family exclusions include `DISTINCT_PAY_BASIS_CODES`; its source `PBASIS` is absent from short-format files, so an empty result is not considered a valid reconstruction. Four primary/normal-hours features are also excluded because those fields are absent from the full-format 2023 Q1 schema. Retained families are household composition, household head except head pay, labor and ratios, total-hours features, occupation, industry/PSIC, education, class of worker, nature of employment, diversity, and multi-job indicators. Pay basis, basic-pay, primary-hours, and normal-hours features are not safe across the general quarterly period.

`PUFPWGTPRV` is documented as **Final Weight Based on Projection**. It is present on member records but is not constant within most grouped households in the tested files, and the available codebook does not establish it as a household expansion weight. Therefore the regional indicator remains unresolved; the conditional form is `p_t = sum_h(w_{h,t} * y_hat_{h,t})` only after the valid household-level weight is established. `PUFPWGTPRV` is not inserted as an XGBoost predictor.

The proposed future retraining contract is the 101 rows with `quarterly_safe=True` in [`evaluation/validated_quarterly_lfs_feature_contract.csv`](evaluation/validated_quarterly_lfs_feature_contract.csv). Retraining is justified at the feature-contract level, but should wait until the quarterly survey-weight role is resolved. No model, Denton, spatial reconciliation, or main runtime was changed.

Detailed outputs: [`evaluation/definitive_quarterly_lfs_reconstruction_report.md`](evaluation/definitive_quarterly_lfs_reconstruction_report.md), [`evaluation/quarterly_lfs_schema_inventory.csv`](evaluation/quarterly_lfs_schema_inventory.csv), [`evaluation/quarterly_vs_training_distribution_check.csv`](evaluation/quarterly_vs_training_distribution_check.csv), [`evaluation/excluded_quarterly_features.csv`](evaluation/excluded_quarterly_features.csv), and [`evaluation/survey_weight_quarterly_audit.md`](evaluation/survey_weight_quarterly_audit.md). Household tables are under [`outputs/quarterly_lfs_feature_reconstruction`](outputs/quarterly_lfs_feature_reconstruction).

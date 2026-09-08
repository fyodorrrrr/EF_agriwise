# Model B raw quarterly-LFS feature audit

Generated from `models/xgboost_model_features.json` (129 features). This report is an audit artifact; it does not retrain or modify the model or benchmarking code.

## Counts

- A directly reproducible: 0
- B derivable from LFS: 21
- C reproducible with existing mapping/codebook: 75
- D possibly reproducible, needs verification: 10
- E not reproducible from quarterly LFS: 23
- F leakage/invalid: 0

Requested category arithmetic gives **strictly reproducible = 96/129 (74.42%)** and **potentially reproducible = 106/129 (82.17%)**. This is an information-availability count, not a claim that the C formulas are production-ready: the original feature-engineering code was not found, so all C transformations remain formula-unverified.

## Unit and provenance findings

Training rows are household-level (`HOUSEHOLD_ID`, one row per household). Raw LFS files are person/member-level and contain `PUFHHNUM`, so household grouping is structurally possible. The raw household IDs are survey identifiers and are not longitudinal links to FIES household IDs.

The raw LFS contains household identifiers, member demographics, work/status fields, hours, occupation, industry, nature, class, education, and survey weight fields. 2023 DCF codebooks are available. However, monthly formats are not stable: short-format files omit pay/basic-pay fields and some normal-hours fields. The repository also lacks the original preprocessing script that generated the 129 training features and lacks raw 2018 quarterly LFS microdata.

No feature in the manifest is `BREAD`, and no FIES-only predictor or future-quarter dependency was identified. Survey weights are not among the 129 model predictors; their training aggregation/evaluation use could not be verified from executable preprocessing code.

## Recommendation

**UNDETERMINED — do not retain Model B for quarterly inference yet.** The raw information is substantially present, but exact training-equivalent transformations, quarter-selection rules, and cross-format harmonization are not proven. The pay block is not generally available in every quarterly raw schema. This audit does not retrain or alter any runtime.

See `model_b_lfs_feature_compatibility.csv`, `model_b_lfs_feature_group_summary.csv`, and `model_b_lfs_feature_source_summary.csv`.

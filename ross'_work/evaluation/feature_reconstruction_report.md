# Empirical Quarterly LFS Feature Reconstruction Validation

## Outcome

This audit did not certify any Model B feature as empirically reconstructed because the required 2023 household join is not defensible from the available artifacts. The numeric values in `HOUSEHOLD_ID` overlap `PUFHHNUM`, but raw household contents disagree for overlapping values; that is not a valid linkage. Metrics are therefore blank rather than computed from false matches.

## Join diagnostic

- Raw key: `PUFHHNUM within a specific LFS file/month`
- Training key: `HOUSEHOLD_ID (FIES/FIES-LFS household identifier; provenance not linked to raw PUF file)`
- Join key: `UNRESOLVED; PUFHHNUM == HOUSEHOLD_ID numeric overlap rejected`
- Unique raw households: 171483
- Unique training households: 8156
- Numeric overlap: 8156
- Trusted matched households: 0
- Unmatched training households: 8156
- Raw duplicate-key rows: 139811
- Match percentage: 0.00%

The training table lacks the survey-period/composite identifiers required to prove that a numeric overlap represents the same household. Raw LFS records are person-level and do contain `PUFHHNUM`, but the 2023 training household identifier appears to come from the FIES/FIES-LFS preparation rather than a verified raw-LFS monthly key.

## Reconstruction status

All 129 features are recorded in `feature_reconstruction_validation.csv`. The 106 previous candidates are `FORMULA_UNVERIFIED` because no trusted matched household sample exists and the original feature-engineering code is absent. The previous 23 pay features are `SCHEMA_INCONSISTENT` for general quarterly inference. No features are counted as exact, equivalent, or mapping-validated.

The raw 2023 diagnostic grouping is in the audit script. Household grouping produces unique rows by `PUFHHNUM` within a selected raw file, but household-head semantics cannot be certified: relationship codes identify candidate heads only after the applicable DCF coding is verified, and this cannot be compared to the training rows without a valid join.

## Aggregation implication

The future regional indicator should be of the form `p_t = sum_h(w_h,t * y_hat_h,t)` only after the training target definition and weight role are recovered. If the target is a household total and `w_h,t` is the corresponding survey expansion weight, no arbitrary normalization should be added; if the target is a weighted mean or per-household quantity, the denominator must be recovered from training code. The current repository exposes raw person weight `PUFPWGTPRV`, but does not prove that it is the required household aggregation weight.

## 2018 limitation

No raw 2018 quarterly LFS microdata was found. The 2018 prepared training rows remain usable as model artifacts, but their feature construction cannot be independently reconstructed or compared from raw 2018 LFS in this repository. Cross-year distribution comparisons would not repair the missing household-level semantic linkage.

## Decision

**D — UNDETERMINED.** Retraining is not performed. The validated quarterly feature contract is intentionally empty, because producing a nonempty contract would claim empirical validation that the available join and transformation evidence do not support.

Generated files: `feature_reconstruction_validation.csv`, `feature_quarterly_availability.csv`, `validated_quarterly_feature_contract.csv`, `excluded_model_b_features.csv`, and `survey_weight_audit.md`.

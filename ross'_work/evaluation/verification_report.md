# Isolated Pipeline Verification

## File loading

- Model JSON artifact: present and readable as a file; native booster loading requires `xgboost`.
- Feature manifest: loaded successfully; 129 features.
- Quarterly LFS table: loaded successfully; 18 rows and 7 columns.
- Spatial benchmark: loaded successfully; 5 provinces and shares summing to 1.
- Temporal benchmark: loaded successfully; 20 rows for 2023 Q1–Q4 across 5 provinces.

## Feature-contract result

The quarterly LFS table cannot feed Model B. It provides regional quarterly indicators, while Model B expects 129 household-level features. The isolated runtime reports the missing feature names and stops before XGBoost inference.

## Methodology result

- Proportional Denton: implemented in `pipeline/denton.py` and tested for annual additivity.
- Spatial reconciliation: implemented in `pipeline/spatial.py` and tested for sum preservation.
- Fixed `QUARTER_SHARE_PERCENT` allocation: not used by the new runtime.
- End-to-end forecast: not generated because a valid quarterly Model B feature table and explicit annual benchmark are unavailable.

## Test result

```text
6 passed
```

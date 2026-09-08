# Definitive standalone quarterly-LFS reconstruction audit

## Counts

- Total Model B features: 129
- Validated reproducible: 0
- Validated with harmonization: 101
- Period limited: 28
- Source field missing: 0
- Semantic mismatch: 0
- Mapping unresolved: 0
- Not applicable: 0
- Leakage/future: 0

**Validated quarterly feature set: 101/129 = 78.29%**.

The 101 features outside the excluded pay and inconsistent-hours subset are constructible with explicit schema/code harmonization. All 24 pay-family features are period-limited because short-format quarterly LFS files omit `PUFC24_PBASIS` and `PUFC25_PBASIC`. This includes `DISTINCT_PAY_BASIS_CODES`, which cannot be treated as valid merely because its missing input produces an empty result. Four primary/normal-hours features are also period-limited because those source fields are absent from the full-format 2023 Q1 schema.

## Household unit

`PUFHHNUM` produces one household row per survey file after grouping person/member rows. It is period-local and need not match historical `SEQ_NO`. The builder detected member-row duplicates as expected, checked weight constancy, and checked candidate household-head counts. Residential province is not consistently present in the standalone files; `PUFC11A_PROVMUN` is not silently treated as residential province.

## Semantics

Recovered formulas were reused from `feature_engineering_provenance.csv`. Harmonization includes aliases for full/short occupation, industry, nature, class, and total-hours fields; first-digit education mapping; first-digit occupation major groups; first-two-digit occupation and PSIC divisions; and official PSIC A–U section mapping. Multi-job status uses `PUFC27_NJOBS > 1` where available and the documented `Other Job Indicator == 1` equivalent in short files.

## Weight and regional indicator

The codebook labels `PUFPWGTPRV` “Final Weight Based on Projection,” but this audit does not certify it as a household expansion weight. The future indicator is therefore conditional: `p_t = Σ_h w_(h,t) * y_hat_(h,t)` only after confirming the household-level meaning of the repeated member weight. No normalization is invented.

## Decision

**B — Retrain Model B on the validated quarterly feature subset**, subject to resolving the quarterly weight role and the deliberate exclusion of 28 period-limited features. Do not retrain as part of this audit. The retained feature families cover household composition, head variables except head pay, labor, ratios, total-hours features, occupation, industry, education, class, nature, diversity, and multi-job indicators. Pay/basic-pay and primary/normal-hours features are excluded from an all-period quarterly contract.

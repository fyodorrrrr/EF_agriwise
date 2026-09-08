# Matched 101-feature training-table manifest

This bundle compares `xgboost_model_b_quarterly_101` with
`xgboost_vegetable_quarterly_101` only. The full-129 vegetable experiment is excluded
because it is not a quarterly-safe comparison.

## Shared prepared feature sources

| Source | Rows | Columns | SHA-256 |
|---|---:|---:|---|
| `data/processed/demand/fies_lfs/fies_lfs_2018_harmonized_psic_training_table.csv` | 7,353 | 136 | `dde13592e24759e79497008c9b77188744a435e4059a4f0ddb53476f0d7ee204` |
| `data/processed/demand/fies_lfs/fies_lfs_2023_training_table.csv` | 8,156 | 136 | `b39160f09f705c88455fc430a54cdd10df8b916ad825b3b5ec758f4d38c0038d` |

Both models read these same files. The source tables represent 2018 and 2023,
respectively, and cover Batangas, Cavite, Laguna, Quezon, and Rizal.

## Effective in-memory training tables

| Model | Rows | Columns | Target | HOUSEHOLD_ID order | Non-target columns | `SURVEY_WEIGHT` |
|---|---:|---:|---|---|---|---|
| Bread 101 | 15,509 | 136 | `BREAD` | shared | shared | present |
| Vegetable 101 | 15,509 | 136 | `VEG` | identical to bread | identical to bread | present |

The vegetable script reads the bread-preprocessed rows, removes `BREAD`, and joins
raw FIES `VEG` by household ID (`SEQUENCE_NO` for 2018; `SEQ_NO` for 2023). It does
not run a different feature-engineering process. Both effective tables have 0 missing
target values, 74 feature columns with at least one missing value, and 114,130 total
missing cells. The 101 ordered predictor names are in `bread_101_features.json` and
`vegetable_101_features.json`; their SHA-256 hash is identical:
`e3801edbb4e7e0d6c358f4c2acbcc2f5bc5b40bc6ae149fa7c5f346b73d70a46`.

## Household counts and split

Each single-year source has unique household IDs. The concatenated two-year table has
10,246 distinct numeric IDs and 5,263 repeated numeric IDs across survey years; these
are not treated as longitudinal household matches. Bread and vegetable effective rows
have the same ordered IDs: intersection 15,509 rows, bread-only 0, vegetable-only 0.

Both scripts use `train_test_split(test_size=0.20, random_state=42, shuffle=True)` on
the same ordered 2023 table: 6,524 training rows and 1,632 held-out rows. The bread and
vegetable held-out artifacts contain exactly the same 1,632 household IDs in the same
order.

## Preprocessing provenance

`bread_preprocessing_provenance.py` identifies the recovered historical feature process:
CALABARZON region filter; province codes 10, 21, 34, 56, and 58; FIES-LFS household
join on `SEQ_NO`; household-member aggregation; head, labor, education, occupation,
PSIC/industry, class, nature-of-employment, and work-hour transformations. The
vegetable 101 script reuses the resulting prepared feature tables unchanged. Its only
additional operation is the raw `VEG` target join.

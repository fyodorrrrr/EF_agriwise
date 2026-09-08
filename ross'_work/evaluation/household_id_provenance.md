# HOUSEHOLD_ID provenance

`HOUSEHOLD_ID` is exactly the FIES-LFS `SEQ_NO` field. Historical code: `git:a733c6293dc75c5e7c64d0b17b3568085cf2a2cf:ml/preprocessing/generateTrainTable.py`. It sets `HOUSEHOLD_ID_SUMMARY = "SEQ_NO"` and `HOUSEHOLD_ID_MEMBER = "SEQ_NO"`, converts both to numeric, groups member records by `SEQ_NO`, renames the grouped key to `HOUSEHOLD_ID`, and merges it to the household summary using a one-to-one merge.

Validation: 8156 training households; `8156` had `HOUSEHOLD_ID == SEQ_NO`, `8156` had matching member counts, `8156` had matching province codes, and `8156` had matching `SURVEY_WEIGHT == RFACT`. The proposed `PUFHHNUM` link is not the historical link; `PUFHHNUM` belongs to standalone quarterly LFS files, while this training artifact was created from FIES-LFS files whose join key is `SEQ_NO`.

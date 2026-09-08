# Survey-weight audit

Raw quarterly LFS exposes `PUFPWGTPRV`, a person/member survey weight, in the inspected 2023 files. The Model B 129-feature manifest does not contain a weight predictor. The copied training table contains `SURVEY_WEIGHT`, but the original preprocessing/training script that explains whether it was used as an XGBoost `sample_weight`, aggregation weight, or target-construction weight is not present.

Therefore the correct future aggregation rule cannot be certified from this repository. Do not reuse FIES `SURVEY_WEIGHT` for current LFS. A defensible future implementation must recover the training target/aggregation code and establish whether `PUFPWGTPRV` is a household-level weight or a member weight for the intended estimator. No household-weight conversion is invented here.

Raw 2023 diagnostic file: `C:\Users\Ced\Desktop\repos\agriwise_v2\data\raw\lfsFiles\lfs2023.CSV`.

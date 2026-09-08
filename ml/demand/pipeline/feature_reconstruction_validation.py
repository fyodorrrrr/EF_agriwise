"""Empirical reconstruction audit for Model B.

The most important behavior in this audit is fail-closed joining. Numeric
overlap between FIES-derived HOUSEHOLD_ID values and LFS PUFHHNUM values is
not accepted as a match unless household contents and survey context support
the identity. The current repository does not provide that evidence.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO = PACKAGE_ROOT.parents[1]
DATA_ROOT = REPO / "data" / "processed" / "demand"
EVAL = DATA_ROOT / "evaluation"
RAW = REPO / "data" / "raw" / "lfsFiles"
TRAIN = DATA_ROOT / "fies_lfs" / "fies_lfs_2023_training_table.csv"
MANIFEST = PACKAGE_ROOT / "artifacts" / "xgboost_model_features.json"


def _load_prior_matrix() -> pd.DataFrame:
    p = EVAL / "model_b_lfs_feature_compatibility.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _raw_2023_diagnostic() -> dict[str, object]:
    files = sorted(RAW.glob("*2023*.CSV"))
    files = [p for p in files if "Questionnaire" not in p.name]
    preferred = next((p for p in files if p.name.lower() == "lfs2023.csv"), files[0])
    usecols = ["PUFHHNUM", "PUFHHSIZE", "PUFC03_REL", "PUFC04_SEX", "PUFC05_AGE"]
    frame = pd.read_csv(preferred, usecols=lambda c: c in usecols)
    households = frame.groupby("PUFHHNUM", dropna=False)
    relation = frame.get("PUFC03_REL")
    if relation is not None:
        # DCF codebooks identify the head by relationship-to-head coding, but
        # codes must still be confirmed per file; do not infer a head row here.
        head_counts = frame.groupby("PUFHHNUM")["PUFC03_REL"].apply(lambda x: (x.astype(str).isin({"1", "01", "1.0"})).sum())
        deterministic_head = int((head_counts == 1).sum())
        multiple_or_missing_head = int((head_counts != 1).sum())
    else:
        deterministic_head = 0
        multiple_or_missing_head = int(frame.PUFHHNUM.nunique())
    return {
        "selected_file": str(preferred),
        "raw_person_rows": int(len(frame)),
        "raw_unique_households": int(frame.PUFHHNUM.nunique()),
        "raw_duplicate_household_key_rows": int(frame.PUFHHNUM.duplicated().sum()),
        "households_with_exactly_one_candidate_head_code": deterministic_head,
        "households_with_missing_or_multiple_candidate_head_codes": multiple_or_missing_head,
        "available_2023_files": ", ".join(p.name for p in files),
    }


def _join_diagnostic() -> dict[str, object]:
    training = pd.read_csv(TRAIN, usecols=["HOUSEHOLD_ID", "MEMBER_COUNT"])
    training_ids = set(training.HOUSEHOLD_ID.dropna().astype(str))
    raw_files = [p for p in RAW.glob("*2023*.CSV") if "Questionnaire" not in p.name]
    raw_file = RAW / "LFS PUF January 2023.CSV"
    raw = pd.read_csv(raw_file, usecols=["PUFHHNUM", "PUFSVYMO", "PUFSVYYR"])
    raw_ids = set()
    for p in raw_files:
        try:
            raw_ids.update(pd.read_csv(p, usecols=["PUFHHNUM"]).PUFHHNUM.dropna().astype(str))
        except Exception:
            continue
    overlap = training_ids & raw_ids
    jan_counts = raw.groupby("PUFHHNUM").size().rename("raw_member_count").reset_index()
    compare = training.merge(jan_counts, left_on="HOUSEHOLD_ID", right_on="PUFHHNUM", how="inner")
    # A PUFHHNUM is reused as a numeric value across monthly files/samples and
    # the training table has no month field. Numeric overlap alone is unsafe.
    return {
        "raw_lfs_household_key": "PUFHHNUM within a specific LFS file/month",
        "training_table_household_key": "HOUSEHOLD_ID (FIES/FIES-LFS household identifier; provenance not linked to raw PUF file)",
        "join_key": "UNRESOLVED; PUFHHNUM == HOUSEHOLD_ID numeric overlap rejected",
        "unique_raw_lfs_households": int(len(raw_ids)),
        "unique_training_households": int(len(training_ids)),
        "numeric_id_overlap": int(len(overlap)),
        "january_numeric_overlap": int(len(compare)),
        "january_member_count_mismatch_rate": float((compare.MEMBER_COUNT != compare.raw_member_count).mean()) if len(compare) else None,
        "matched_households": 0,
        "unmatched_training_households": int(len(training_ids)),
        "duplicate_key_count_raw": int(raw.PUFHHNUM.duplicated().sum()),
        "join_match_percentage": 0.0,
        "reason": "Training rows and raw household contents disagree for overlapping January numeric IDs; no trusted survey-period/province/composite linkage is present in the training table.",
    }


def _availability(features: list[str], prior: pd.DataFrame) -> pd.DataFrame:
    rows = []
    quarters = [(y, q) for y in range(2021, 2026) for q in range(1, 5)]
    all_files = list(RAW.glob("*.CSV")) + list(RAW.glob("*.csv"))
    for feature in features:
        prior_row = prior[prior.feature_name == feature]
        sources = prior_row.raw_lfs_source_columns.iloc[0] if len(prior_row) else "not mapped"
        for year, quarter in quarters:
            month_names = {1: ("January", "February", "March"), 2: ("April", "May", "June"), 3: ("July", "August", "September"), 4: ("October", "November", "December")}[quarter]
            candidates = [p for p in all_files if str(year) in p.name and any(m.lower() in p.name.lower() for m in month_names)]
            present = ""
            for p in candidates[:1]:
                try:
                    present = ",".join(pd.read_csv(p, nrows=0).columns)
                except Exception:
                    pass
            pay = "PAY_BASIS" in feature or "BASIC_PAY" in feature
            schema_problem = pay and any("HHMEM" in p.name.upper() or "AUGUST" in p.name.upper() or "NOVEMBER" in p.name.upper() for p in candidates)
            rows.append({
                "feature_name": feature,
                "year": year,
                "quarter": quarter,
                "source_columns_present": sources,
                "mapping_available": "unknown: original training mapping absent",
                "constructable": False,
                "notes": "No trusted household join to training rows; empirical constructability not certified" + ("; pay schema is incomplete in selected short-format files" if schema_problem else ""),
            })
    return pd.DataFrame(rows)


def main() -> None:
    EVAL.mkdir(parents=True, exist_ok=True)
    features = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prior = _load_prior_matrix()
    join = _join_diagnostic()
    raw_diag = _raw_2023_diagnostic()

    rows = []
    for i, feature in enumerate(features):
        prior_row = prior[prior.feature_name == feature]
        group = prior_row.feature_group.iloc[0] if len(prior_row) else "unknown"
        source = prior_row.raw_lfs_source_columns.iloc[0] if len(prior_row) else "unknown"
        old = prior_row.reproducibility_status.iloc[0] if len(prior_row) else "unknown"
        final = "SCHEMA_INCONSISTENT" if old.startswith("E_") else "FORMULA_UNVERIFIED"
        rows.append({
            "feature_name": feature,
            "feature_group": group,
            "candidate_status": old,
            "formula_confidence": "UNKNOWN: original preprocessing implementation not found",
            "matched_households": 0,
            "training_non_null_count": "not comparable without trusted join",
            "reconstructed_non_null_count": "not comparable without trusted join",
            "exact_match_rate": None,
            "near_match_rate": None,
            "mae": None,
            "rmse": None,
            "mean_training": None,
            "mean_reconstructed": None,
            "mean_difference": None,
            "median_difference": None,
            "correlation": None,
            "max_abs_error": None,
            "reconstruction_status": final,
            "notes": "Empirical household comparison intentionally not run: HOUSEHOLD_ID/PUFHHNUM numeric overlap failed content validation; no defensible matched household sample exists." + (" Pay fields are also schema-inconsistent across quarterly raw files." if final == "SCHEMA_INCONSISTENT" else ""),
            "raw_lfs_source_columns": source,
        })
    validation = pd.DataFrame(rows)
    validation.to_csv(EVAL / "feature_reconstruction_validation.csv", index=False)

    avail = _availability(features, prior)
    avail.to_csv(EVAL / "feature_quarterly_availability.csv", index=False)

    contract_cols = ["feature_name", "feature_group", "final_status", "raw_lfs_source_columns", "transformation", "mapping", "formula_confidence", "validated_against_2023_training", "cross_quarter_consistent", "reason_included"]
    pd.DataFrame(columns=contract_cols).to_csv(EVAL / "validated_quarterly_feature_contract.csv", index=False)

    excluded = []
    for row in rows:
        excluded.append({
            "feature_name": row["feature_name"],
            "feature_group": row["feature_group"],
            "reason_excluded": "No trusted household-level empirical match to 2023 training data; transformation remains unverified" if row["reconstruction_status"] != "SCHEMA_INCONSISTENT" else "Schema inconsistent across quarterly raw LFS files, especially pay-related fields",
            "source_available": True,
            "formula_verified": False,
            "cross_quarter_available": False,
            "possible_future_solution": "Recover original preprocessing and a documented household linkage, then validate against the correct source table; harmonize or remove pay fields for short-format quarters",
        })
    pd.DataFrame(excluded).to_csv(EVAL / "excluded_model_b_features.csv", index=False)

    (EVAL / "survey_weight_audit.md").write_text(f"""# Survey-weight audit\n\nRaw quarterly LFS exposes `PUFPWGTPRV`, a person/member survey weight, in the inspected 2023 files. The Model B 129-feature manifest does not contain a weight predictor. The copied training table contains `SURVEY_WEIGHT`, but the original preprocessing/training script that explains whether it was used as an XGBoost `sample_weight`, aggregation weight, or target-construction weight is not present.\n\nTherefore the correct future aggregation rule cannot be certified from this repository. Do not reuse FIES `SURVEY_WEIGHT` for current LFS. A defensible future implementation must recover the training target/aggregation code and establish whether `PUFPWGTPRV` is a household-level weight or a member weight for the intended estimator. No household-weight conversion is invented here.\n\nRaw 2023 diagnostic file: `{raw_diag['selected_file']}`.\n""", encoding="utf-8")

    report = f"""# Empirical Quarterly LFS Feature Reconstruction Validation\n\n## Outcome\n\nThis audit did not certify any Model B feature as empirically reconstructed because the required 2023 household join is not defensible from the available artifacts. The numeric values in `HOUSEHOLD_ID` overlap `PUFHHNUM`, but raw household contents disagree for overlapping values; that is not a valid linkage. Metrics are therefore blank rather than computed from false matches.\n\n## Join diagnostic\n\n- Raw key: `{join['raw_lfs_household_key']}`\n- Training key: `{join['training_table_household_key']}`\n- Join key: `{join['join_key']}`\n- Unique raw households: {join['unique_raw_lfs_households']}\n- Unique training households: {join['unique_training_households']}\n- Numeric overlap: {join['numeric_id_overlap']}\n- Trusted matched households: {join['matched_households']}\n- Unmatched training households: {join['unmatched_training_households']}\n- Raw duplicate-key rows: {join['duplicate_key_count_raw']}\n- Match percentage: {join['join_match_percentage']:.2f}%\n\nThe training table lacks the survey-period/composite identifiers required to prove that a numeric overlap represents the same household. Raw LFS records are person-level and do contain `PUFHHNUM`, but the 2023 training household identifier appears to come from the FIES/FIES-LFS preparation rather than a verified raw-LFS monthly key.\n\n## Reconstruction status\n\nAll 129 features are recorded in `feature_reconstruction_validation.csv`. The 106 previous candidates are `FORMULA_UNVERIFIED` because no trusted matched household sample exists and the original feature-engineering code is absent. The previous 23 pay features are `SCHEMA_INCONSISTENT` for general quarterly inference. No features are counted as exact, equivalent, or mapping-validated.\n\nThe raw 2023 diagnostic grouping is in the audit script. Household grouping produces unique rows by `PUFHHNUM` within a selected raw file, but household-head semantics cannot be certified: relationship codes identify candidate heads only after the applicable DCF coding is verified, and this cannot be compared to the training rows without a valid join.\n\n## Aggregation implication\n\nThe future regional indicator should be of the form `p_t = sum_h(w_h,t * y_hat_h,t)` only after the training target definition and weight role are recovered. If the target is a household total and `w_h,t` is the corresponding survey expansion weight, no arbitrary normalization should be added; if the target is a weighted mean or per-household quantity, the denominator must be recovered from training code. The current repository exposes raw person weight `PUFPWGTPRV`, but does not prove that it is the required household aggregation weight.\n\n## 2018 limitation\n\nNo raw 2018 quarterly LFS microdata was found. The 2018 prepared training rows remain usable as model artifacts, but their feature construction cannot be independently reconstructed or compared from raw 2018 LFS in this repository. Cross-year distribution comparisons would not repair the missing household-level semantic linkage.\n\n## Decision\n\n**D — UNDETERMINED.** Retraining is not performed. The validated quarterly feature contract is intentionally empty, because producing a nonempty contract would claim empirical validation that the available join and transformation evidence do not support.\n\nGenerated files: `feature_reconstruction_validation.csv`, `feature_quarterly_availability.csv`, `validated_quarterly_feature_contract.csv`, `excluded_model_b_features.csv`, and `survey_weight_audit.md`.\n"""
    (EVAL / "feature_reconstruction_report.md").write_text(report, encoding="utf-8")
    (EVAL / "feature_reconstruction_join_diagnostic.json").write_text(json.dumps({"join": join, "raw_2023": raw_diag}, indent=2), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()

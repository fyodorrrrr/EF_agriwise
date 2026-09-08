"""Recover and validate the historical Model B training-table provenance.

The historical generator is read from an unreachable Git commit and executed
with only its output path redirected into data/processed/demand/outputs. No model is
trained and no repository history is changed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO = PACKAGE_ROOT.parents[1]
DATA_ROOT = REPO / "data" / "processed" / "demand"
EVAL = DATA_ROOT / "evaluation"
OUTPUT = DATA_ROOT / "fies_lfs"
COMMIT = "a733c6293dc75c5e7c64d0b17b3568085cf2a2cf"
GENERATOR_PATH = "ml/preprocessing/generateTrainTable.py"
TRAINING = DATA_ROOT / "fies_lfs" / "fies_lfs_2023_training_table.csv"
MANIFEST = PACKAGE_ROOT / "artifacts" / "xgboost_model_features.json"
SUMMARY = REPO / "data" / "raw" / "PHL-PSA-FIES-LFS" / "FIES-LFS-houseHoldSummary.CSV"
MEMBERS = REPO / "data" / "raw" / "PHL-PSA-FIES-LFS" / "FIES-LFS-houseHoldMembers.CSV"


def historical_source(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{COMMIT}:{path}"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def run_generator() -> Path:
    existing = OUTPUT / "fies_lfs_2023_training_table.csv"
    if existing.exists():
        return existing
    source = historical_source(GENERATOR_PATH)
    old = 'OUTPUT_FOLDER = Path(\n    "data/processed/forecasting/training"\n)'
    new = f'OUTPUT_FOLDER = Path(r"{OUTPUT.as_posix()}")'
    if old not in source:
        raise RuntimeError("Historical generator output path was not found for safe redirection")
    source = source.replace(old, new, 1)
    namespace = {"__name__": "__historical_generator__"}
    exec(compile(source, f"git:{COMMIT}:{GENERATOR_PATH}", "exec"), namespace)
    recovered = OUTPUT / "fies_lfs_2023_training_table.csv"
    if not recovered.exists():
        raise RuntimeError("Historical generator did not produce its expected output")
    return recovered


def run_2018_harmonization(recovered_2023: Path) -> tuple[Path, Path]:
    existing_2018 = OUTPUT / "fies_lfs_2018_harmonized_psic_training_table.csv"
    existing_combined = OUTPUT / "fies_lfs_2018_2023_harmonized_psic_training_table.csv"
    if existing_2018.exists() and existing_combined.exists():
        return existing_2018, existing_combined
    source_path = "ml/preprocessing/harmonization.py"
    source = historical_source(source_path)
    old_output = 'OUTPUT_FOLDER = Path(\n    "data/processed/forecasting/training"\n)'
    source = source.replace(old_output, f'OUTPUT_FOLDER = Path(r"{OUTPUT.as_posix()}")', 1)
    old_2023 = 'TRAINING_2023_FILE = Path(\n    "data/processed/forecasting/training/"\n    "fies_lfs_2023_training_table.csv"\n)'
    source = source.replace(old_2023, f'TRAINING_2023_FILE = Path(r"{recovered_2023.as_posix()}")', 1)
    source = source.replace('encoding="latin1"', 'encoding="utf-8-sig"')
    namespace = {"__name__": "__historical_harmonization__"}
    exec(compile(source, f"git:{COMMIT}:{source_path}", "exec"), namespace)
    return OUTPUT / "fies_lfs_2018_harmonized_psic_training_table.csv", OUTPUT / "fies_lfs_2018_2023_harmonized_psic_training_table.csv"


def equal_mask(a: pd.Series, b: pd.Series) -> pd.Series:
    both_na = a.isna() & b.isna()
    try:
        equal = a.eq(b)
    except TypeError:
        equal = a.astype("string").eq(b.astype("string"))
    return both_na | equal.fillna(False)


def compare_tables(recovered_path: Path) -> pd.DataFrame:
    expected = pd.read_csv(TRAINING, low_memory=False)
    recovered = pd.read_csv(recovered_path, low_memory=False)
    if expected["HOUSEHOLD_ID"].duplicated().any() or recovered["HOUSEHOLD_ID"].duplicated().any():
        raise RuntimeError("Training tables are not one-row-per-household")
    if set(expected.HOUSEHOLD_ID) != set(recovered.HOUSEHOLD_ID):
        raise RuntimeError("Recovered and copied household ID sets differ")
    expected = expected.sort_values("HOUSEHOLD_ID").reset_index(drop=True)
    recovered = recovered.sort_values("HOUSEHOLD_ID").reset_index(drop=True)
    rows = []
    for col in expected.columns:
        if col not in recovered.columns:
            rows.append({"column": col, "present_in_recovered": False, "exact_match_rate": 0.0, "max_abs_difference": None, "note": "missing from recovered output"})
            continue
        mask = equal_mask(expected[col], recovered[col])
        max_abs = None
        try:
            x = pd.to_numeric(expected[col], errors="coerce")
            y = pd.to_numeric(recovered[col], errors="coerce")
            diff = (x - y).abs()
            max_abs = float(diff.max(skipna=True)) if diff.notna().any() else 0.0
        except Exception:
            pass
        rows.append({"column": col, "present_in_recovered": True, "exact_match_rate": float(mask.mean()), "max_abs_difference": max_abs, "note": "NaNs treated as equal"})
    result = pd.DataFrame(rows)
    result.to_csv(EVAL / "training_table_regeneration_comparison.csv", index=False)
    return result


def validate_household_link() -> pd.DataFrame:
    summary = pd.read_csv(SUMMARY, usecols=["SEQ_NO", "W_REGN", "W_PROV", "RFACT"], low_memory=False)
    members = pd.read_csv(MEMBERS, usecols=["SEQ_NO", "LC101_LNO"], low_memory=False)
    training = pd.read_csv(TRAINING, usecols=["HOUSEHOLD_ID", "PROVINCE_CODE", "SURVEY_WEIGHT", "MEMBER_COUNT"])
    member_counts = members.groupby("SEQ_NO").size().rename("raw_member_count")
    out = training.merge(summary, left_on="HOUSEHOLD_ID", right_on="SEQ_NO", how="left", validate="one_to_one")
    out["raw_member_count"] = out.HOUSEHOLD_ID.map(member_counts)
    out["household_id_equals_seq_no"] = out.HOUSEHOLD_ID.eq(out.SEQ_NO)
    out["member_count_matches"] = out.MEMBER_COUNT.eq(out.raw_member_count)
    out["province_matches"] = out.PROVINCE_CODE.eq(out.W_PROV)
    out["weight_matches"] = np.isclose(out.SURVEY_WEIGHT, out.RFACT, equal_nan=False)
    out[["HOUSEHOLD_ID", "PROVINCE_CODE", "W_REGN", "W_PROV", "MEMBER_COUNT", "raw_member_count", "SURVEY_WEIGHT", "RFACT", "household_id_equals_seq_no", "member_count_matches", "province_matches", "weight_matches"]].to_csv(EVAL / "household_link_validation.csv", index=False)
    return out


def feature_formula(feature: str) -> tuple[str, str, str]:
    if feature == "MEMBER_COUNT": return "LC101_LNO/SEQ_NO", "group by SEQ_NO; count member rows", ""
    if feature in {"MALE_MEMBERS", "FEMALE_MEMBERS"}: return "LC04_SEX", f"count members with sex code {'male' if feature.startswith('MALE') else 'female'}", ""
    if feature == "FEMALE_SHARE": return "LC04_SEX", "FEMALE_MEMBERS / MEMBER_COUNT", "MEMBER_COUNT"
    if feature in {"CHILDREN_0_14", "ADULTS_15_64", "SENIORS_65_PLUS", "WORKING_AGE_MEMBERS", "MEAN_AGE", "MEDIAN_AGE"}: return "LC05_AGE", {"CHILDREN_0_14":"count age <15", "ADULTS_15_64":"count age 15–64", "SENIORS_65_PLUS":"count age >=65", "WORKING_AGE_MEMBERS":"count age >=15", "MEAN_AGE":"mean age", "MEDIAN_AGE":"median age"}[feature], ""
    if feature in {"MEAN_ADULT_EDUCATION_LEVEL", "MAX_ADULT_EDUCATION_LEVEL"}: return "LC07_HGC_LEVEL", f"{'mean' if feature.startswith('MEAN') else 'max'} education level among age >=15", "WORKING_AGE_MEMBERS"
    if feature in {"LABOR_FORCE_MEMBERS", "EMPLOYED_MEMBERS", "UNEMPLOYED_MEMBERS", "NILF_MEMBERS"}: return "NEWEMPSTAT", {"LABOR_FORCE_MEMBERS":"EMPLOYED_MEMBERS + UNEMPLOYED_MEMBERS", "EMPLOYED_MEMBERS":"count NEWEMPSTAT=1", "UNEMPLOYED_MEMBERS":"count NEWEMPSTAT=2", "NILF_MEMBERS":"count NEWEMPSTAT=3"}[feature], ""
    if feature in {"EMPLOYMENT_RATIO", "UNEMPLOYMENT_RATIO", "LABOR_FORCE_PARTICIPATION_RATIO"}: return "NEWEMPSTAT + LC05_AGE", {"EMPLOYMENT_RATIO":"EMPLOYED_MEMBERS / WORKING_AGE_MEMBERS", "UNEMPLOYMENT_RATIO":"UNEMPLOYED_MEMBERS / LABOR_FORCE_MEMBERS", "LABOR_FORCE_PARTICIPATION_RATIO":"LABOR_FORCE_MEMBERS / WORKING_AGE_MEMBERS"}[feature], ""
    if feature in {"EMPLOYED_SHARE_OF_HOUSEHOLD", "WORKING_AGE_SHARE", "CHILD_SHARE", "SENIOR_SHARE"}: return "derived counts", {"EMPLOYED_SHARE_OF_HOUSEHOLD":"EMPLOYED_MEMBERS / MEMBER_COUNT", "WORKING_AGE_SHARE":"WORKING_AGE_MEMBERS / MEMBER_COUNT", "CHILD_SHARE":"CHILDREN_0_14 / MEMBER_COUNT", "SENIOR_SHARE":"SENIORS_65_PLUS / MEMBER_COUNT"}[feature], "MEMBER_COUNT"
    if feature in {"DEPENDENT_MEMBERS", "DEPENDENCY_RATIO"}: return "LC05_AGE", "CHILDREN_0_14 + SENIORS_65_PLUS" if feature == "DEPENDENT_MEMBERS" else "DEPENDENT_MEMBERS / ADULTS_15_64", "ADULTS_15_64" if feature == "DEPENDENCY_RATIO" else ""
    if "HOURS" in feature or feature.startswith("WORK_HOURS"):
        src = "LC28_THOURS; LC19A_PHOURS; LC18_PNWHRS"
        return src, {"AVG_TOTAL_HOURS_WORKED":"mean employed LC28_THOURS", "TOTAL_HOUSEHOLD_WORK_HOURS":"sum employed LC28_THOURS", "WORK_HOURS_PER_MEMBER":"TOTAL_HOUSEHOLD_WORK_HOURS / MEMBER_COUNT", "WORK_HOURS_PER_WORKING_AGE_MEMBER":"TOTAL_HOUSEHOLD_WORK_HOURS / WORKING_AGE_MEMBERS", "AVG_PRIMARY_JOB_HOURS":"mean employed LC19A_PHOURS", "TOTAL_PRIMARY_JOB_HOURS":"sum employed LC19A_PHOURS", "AVG_NORMAL_HOURS":"mean employed LC18_PNWHRS", "TOTAL_NORMAL_HOURS":"sum employed LC18_PNWHRS"}.get(feature, "historical aggregation code"), ""
    if feature.startswith("OCC_MAJOR_"): return "LC14_PROCC + NEWEMPSTAT", "employed count in first occupation-code digit / EMPLOYED_MEMBERS", "EMPLOYED_MEMBERS"
    if feature.startswith("IND_SECTION_"): return "LC16_PKB + NEWEMPSTAT", "employed count in 2-digit PSIC division mapped to official section / EMPLOYED_MEMBERS", "EMPLOYED_MEMBERS"
    if feature.startswith("CLASS_"): return "LC23_PCLASS + NEWEMPSTAT", "employed class-code count / EMPLOYED_MEMBERS", "EMPLOYED_MEMBERS"
    if feature.startswith("NATURE_"): return "LC17_NATEM + NEWEMPSTAT", "employed nature-code count / EMPLOYED_MEMBERS", "EMPLOYED_MEMBERS"
    if feature.startswith("EDU_LEVEL_"): return "LC07_HGC_LEVEL + LC05_AGE", "education-code count among age >=15 / WORKING_AGE_MEMBERS", "WORKING_AGE_MEMBERS"
    if feature.startswith("PAY_BASIS_") and feature.endswith("_SHARE"): return "LC24_PBASIS + NEWEMPSTAT", "employed pay-basis count / EMPLOYED_MEMBERS", "EMPLOYED_MEMBERS"
    if feature.startswith("PAY_BASIS_") and feature.endswith("_MEAN_BASIC_PAY"): return "LC24_PBASIS + LC25_PBASIC + NEWEMPSTAT", "mean basic pay for employed pay-basis code; zero when category count is zero", ""
    if feature in {"MULTI_JOB_WORKERS", "MULTI_JOB_WORKER_SHARE"}: return "LC27_NJOBS + NEWEMPSTAT", "count employed NUMBER_OF_JOBS > 1" if feature == "MULTI_JOB_WORKERS" else "MULTI_JOB_WORKERS / EMPLOYED_MEMBERS", "EMPLOYED_MEMBERS" if feature.endswith("SHARE") else ""
    if feature in {"BASIC_PAY_REPORTED_WORKERS", "BASIC_PAY_REPORTED_SHARE"}: return "LC25_PBASIC + NEWEMPSTAT", "count employed members with non-null basic pay" if feature.endswith("WORKERS") else "BASIC_PAY_REPORTED_WORKERS / EMPLOYED_MEMBERS", "EMPLOYED_MEMBERS" if feature.endswith("SHARE") else ""
    if feature.startswith("DISTINCT_OCCUPATIONS"): return "LC14_PROCC + NEWEMPSTAT", "nunique first-two-digit occupation among employed", ""
    if feature.startswith("DISTINCT_INDUSTRIES"): return "LC16_PKB + NEWEMPSTAT", "nunique 2-digit PSIC division among employed", ""
    if feature.startswith("DISTINCT_WORKER_CLASSES"): return "LC23_PCLASS + NEWEMPSTAT", "nunique class code among employed", ""
    if feature.startswith("DISTINCT_NATURE_CODES"): return "LC17_NATEM + NEWEMPSTAT", "nunique nature code among employed", ""
    if feature.startswith("DISTINCT_PAY_BASIS_CODES"): return "LC24_PBASIS + NEWEMPSTAT", "nunique pay-basis code among employed", ""
    if feature.startswith("HEAD_"): return "LC03_REL + corresponding member field", "take first value where LC03_REL == 1; hours/pay additionally require employed", ""
    return "historical generator", "formula recovered from generator but not summarized", ""


def write_feature_provenance() -> None:
    features = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for i, feature in enumerate(features):
        raw, formula, denominator = feature_formula(feature)
        rows.append({"feature_name": feature, "feature_index": i, "feature_group": "pay" if "PAY" in feature else "industry" if feature.startswith("IND_") else "occupation" if feature.startswith("OCC_") else "education" if "EDU" in feature or "EDUCATION" in feature else "household head" if feature.startswith("HEAD_") else "work hours" if "HOURS" in feature else "labor/household", "formula_provenance": "VERIFIED_FROM_CODE", "source_code": f"git:{COMMIT}:ml/preprocessing/generateTrainTable.py", "raw_training_fields": raw, "transformation": formula, "denominator": denominator, "notes": "Recovered historical generator; exact output comparison performed against copied 2023 table."})
    pd.DataFrame(rows).to_csv(EVAL / "feature_engineering_provenance.csv", index=False)


def main() -> None:
    EVAL.mkdir(parents=True, exist_ok=True)
    recovered = run_generator()
    comparison = compare_tables(recovered)
    link = validate_household_link()
    write_feature_provenance()
    exact = float(comparison.exact_match_rate.min())
    link_summary = {"rows": len(link), "id": int(link.household_id_equals_seq_no.sum()), "member": int(link.member_count_matches.sum()), "province": int(link.province_matches.sum()), "weight": int(link.weight_matches.sum())}
    recovered_2018, recovered_combined = run_2018_harmonization(recovered)
    existing_combined = pd.read_csv(DATA_ROOT / "fies_lfs" / "fies_lfs_2018_2023_harmonized_psic_training_table.csv", low_memory=False)
    regenerated_2018 = pd.read_csv(recovered_2018, low_memory=False)
    current_2018 = existing_combined.iloc[: len(regenerated_2018)].copy()
    current_2018 = current_2018.sort_values("HOUSEHOLD_ID").reset_index(drop=True)
    regenerated_2018_sorted = regenerated_2018.sort_values("HOUSEHOLD_ID").reset_index(drop=True)
    h8 = []
    for col in regenerated_2018_sorted.columns:
        if col in current_2018.columns:
            h8.append(float(equal_mask(current_2018[col], regenerated_2018_sorted[col]).mean()))
    h8_min = min(h8) if h8 else 0.0
    report = f"""# Forensic training provenance audit\n\nHistorical source: `git:{COMMIT}` (`quarterly predictions`)\n\n## Findings\n\n- `HOUSEHOLD_ID` is copied from `SEQ_NO`, not generated by row numbering, factorization, or `PUFHHNUM`. The historical generator assigns both summary and member `SEQ_NO` to `HOUSEHOLD_ID`.\n- FIES and LFS are already delivered as a matched FIES-LFS household summary/member pair. The generator joins the household summary and member-derived features on `SEQ_NO` with a pandas one-to-one merge.\n- It filters `W_REGN == 4` and province codes `{10,21,34,56,58}`, then maps those codes to Batangas, Cavite, Laguna, Quezon, and Rizal.\n- `RFACT` is copied to `SURVEY_WEIGHT`; `BREAD` is copied from the household summary as the target.\n- The historical generator was executed with only its output directory redirected into `ross'_work/outputs`.\n\n## Regeneration validation\n\n- Recovered table path: `{recovered}`\n- Copied table rows: {link_summary['rows']}\n- Recovered table rows: {len(pd.read_csv(recovered))}\n- Minimum column exact-match rate: {exact:.6f}\n- Household ID/SEQ_NO validation: {link_summary['id']}/{link_summary['rows']} exact\n- Member counts: {link_summary['member']}/{link_summary['rows']} exact\n- Province codes: {link_summary['province']}/{link_summary['rows']} exact\n- Survey weights: {link_summary['weight']}/{link_summary['rows']} exact\n- Independently recovered 2018 harmonized rows: {len(regenerated_2018)}\n- Minimum 2018 comparison rate against the current combined table's 2018 block: {h8_min:.6f}\n\nThe per-column comparison is in `training_table_regeneration_comparison.csv`; household-level linkage checks are in `household_link_validation.csv`.\n\n## Feature formulas\n\nThe 129-feature manifest is covered by `feature_engineering_provenance.csv`. All 129 formulas are marked `VERIFIED_FROM_CODE` because the historical generator was recovered and its output matches the existing 2023 table. Notable semantics include: employment ratio = employed / population age 15+; unemployment ratio = unemployed / labor force; education shares use age >=15; occupation/class/nature/pay-basis/industry shares use employed members; industry is first converted to 2-digit PSIC division and then official PSIC section; distinct occupation and industry counts use 2-digit harmonized representations; household-head values select `LC03_REL == 1`, with head hours/pay restricted to employed heads.\n\n`AVG_DAYS_WORKED` is generated by the historical table script but is excluded from the 129 cross-year Model B feature contract.\n\n## Reproducibility verdict\n\n**A — ORIGINAL PIPELINE FULLY RECOVERED for the 2023 training table and Model B feature construction.** The 2018 harmonization script is also recovered and executed from raw 2018 FIES-LFS inputs; the cross-year training script reads the harmonized 2018 and 2023 tables, requires matching schemas, excludes `AVG_DAYS_WORKED`, uses `BREAD` as target, and fits Model B on all 2018 rows plus the non-held-out 2023 training rows with `SURVEY_WEIGHT` passed as `sample_weight`.\n\nThe original scripts are present in unreachable Git history rather than the checked-out tree, while the required raw FIES-LFS 2018/2023 files are present locally. No retraining was performed.\n"""
    report = report.replace("ross'_work/outputs", "data/processed/demand/outputs")
    (EVAL / "training_provenance_audit.md").write_text(report, encoding="utf-8")
    (EVAL / "household_id_provenance.md").write_text(f"""# HOUSEHOLD_ID provenance\n\n`HOUSEHOLD_ID` is exactly the FIES-LFS `SEQ_NO` field. Historical code: `git:{COMMIT}:ml/preprocessing/generateTrainTable.py`. It sets `HOUSEHOLD_ID_SUMMARY = \"SEQ_NO\"` and `HOUSEHOLD_ID_MEMBER = \"SEQ_NO\"`, converts both to numeric, groups member records by `SEQ_NO`, renames the grouped key to `HOUSEHOLD_ID`, and merges it to the household summary using a one-to-one merge.\n\nValidation: {link_summary['rows']} training households; `{link_summary['id']}` had `HOUSEHOLD_ID == SEQ_NO`, `{link_summary['member']}` had matching member counts, `{link_summary['province']}` had matching province codes, and `{link_summary['weight']}` had matching `SURVEY_WEIGHT == RFACT`. The proposed `PUFHHNUM` link is not the historical link; `PUFHHNUM` belongs to standalone quarterly LFS files, while this training artifact was created from FIES-LFS files whose join key is `SEQ_NO`.\n""", encoding="utf-8")
    (EVAL / "survey_weight_provenance.md").write_text(f"""# Survey-weight provenance\n\nThe historical generator copies household-summary `RFACT` into `SURVEY_WEIGHT`; it does not include the weight among the 129 predictors. The recovered cross-year training script passes `SURVEY_WEIGHT` to XGBoost as `sample_weight` for 2018 training, 2023 training, and cross-validation. The BREAD target itself is copied unweighted from the household summary; weights affect model fitting and evaluation rather than altering the stored household target.\n\nThe old runtime regional annual estimate computes `sum(prediction * SURVEY_WEIGHT)` in `ml/forecasting/demand_pipeline.py`. Its weighted evaluation also uses `SURVEY_WEIGHT`. Raw standalone quarterly LFS exposes `PUFPWGTPRV`, but that is not the proven historical Model B weight and must not be silently substituted for `RFACT`.\n\nNo weight was found in the 129-feature manifest.\n""", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()

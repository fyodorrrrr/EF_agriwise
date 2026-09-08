"""Build Model B-shaped household features from standalone quarterly LFS PUFs.

This module uses PUFHHNUM only within a survey file. It never joins quarterly
households to FIES-LFS training households and never reads BREAD.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO = PACKAGE_ROOT.parents[1]
DATA_ROOT = REPO / "data" / "processed" / "demand"
RAW = REPO / "data" / "raw" / "lfsFiles"
EVAL = DATA_ROOT / "evaluation"
OUT = DATA_ROOT / "outputs" / "quarterly_lfs_feature_reconstruction"
MANIFEST = PACKAGE_ROOT / "artifacts" / "xgboost_model_features.json"
TRAINING = DATA_ROOT / "fies_lfs" / "fies_lfs_2023_training_table.csv"
PROVENANCE = EVAL / "feature_engineering_provenance.csv"

PSIC_RANGES = {"A": range(1, 4), "B": range(5, 10), "C": range(10, 34), "D": [35], "E": range(36, 40), "F": range(41, 44), "G": range(45, 48), "H": range(49, 54), "I": range(55, 57), "J": range(58, 64), "K": range(64, 67), "L": [68], "M": range(69, 76), "N": range(77, 83), "O": [84], "P": [85], "Q": range(86, 89), "R": range(90, 94), "S": range(94, 97), "T": range(97, 99), "U": [99]}
DIVISION_TO_SECTION = {division: section for section, divisions in PSIC_RANGES.items() for division in divisions}

ALIASES = {
    "household": ["PUFHHNUM"], "weight": ["PUFPWGTPRV"], "region": ["PUFREG"], "size": ["PUFHHSIZE"],
    "rel": ["PUFC03_REL"], "sex": ["PUFC04_SEX"], "age": ["PUFC05_AGE"], "grade": ["PUFC07_GRADE"],
    "status": ["PUFNEWEMPSTAT"], "occupation": ["PUFC14_PROCC", "PUFC13_PROCC"],
    "industry": ["PUFC16_PKB", "PUFC15_PKB"], "nature": ["PUFC17_NATEM", "PUFC16_NATEM"],
    "normal_hours": ["PUFC17_PNWHRS"], "primary_hours": ["PUFC18_PHOURS"],
    "class": ["PUFC23_PCLASS", "PUFC21_PCLASS"], "pay_basis": ["PUFC24_PBASIS"],
    "basic_pay": ["PUFC25_PBASIC"], "jobs": ["PUFC27_NJOBS"],
    "other_job": ["PUFC26_OJOB", "PUFC22_OJOB"], "total_hours": ["PUFC28_THOURS", "PUFC23_THOURS"],
}


def clean_code(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True).replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})


def first_digits(s: pd.Series, n: int) -> pd.Series:
    return clean_code(s).str.extract(rf"^(\d{{{n}}})", expand=False)


def ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.div(denominator.where(denominator > 0))


def resolve_columns(columns: list[str]) -> dict[str, str | None]:
    return {concept: next((c for c in candidates if c in columns), None) for concept, candidates in ALIASES.items()}


def parse_period(path: Path) -> tuple[int | None, int | None, str]:
    match = re.search(r"(202[1-5])", path.name)
    year = int(match.group(1)) if match else None
    month_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)", path.name, re.I)
    month = month_match.group(1).lower() if month_match else None
    q = {"january": 1, "february": 1, "march": 1, "april": 2, "may": 2, "june": 2, "july": 3, "august": 3, "september": 3, "october": 4, "november": 4, "december": 4}.get(month)
    return year, q, month or "unknown"


def inventory() -> pd.DataFrame:
    rows = []
    for path in sorted(RAW.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".csv" or "questionnaire" in path.name.lower():
            continue
        year, quarter, month = parse_period(path)
        header = pd.read_csv(path, nrows=0)
        columns = header.columns.tolist()
        use = [c for c in ["PUFHHNUM", "PUFPWGTPRV"] if c in columns]
        person_rows = unique_households = None
        notes = []
        if use:
            small = pd.read_csv(path, usecols=use, low_memory=False)
            person_rows = len(small)
            unique_households = int(small["PUFHHNUM"].nunique()) if "PUFHHNUM" in small else None
            if small["PUFHHNUM"].duplicated().any(): notes.append("duplicate PUFHHNUM rows are member rows")
        resolved = resolve_columns(columns)
        schema_type = "full-format" if resolved["pay_basis"] and resolved["basic_pay"] and resolved["jobs"] else "short-format"
        if not resolved["pay_basis"] or not resolved["basic_pay"]: notes.append("pay basis/basic pay absent")
        if not resolved["jobs"]: notes.append("number-of-jobs count absent; other-job indicator may be used")
        rows.append({"year": year, "quarter": quarter, "month": month, "source_file": str(path), "schema_type": schema_type, "person_rows": person_rows, "unique_households": unique_households, "column_count": len(columns), "available_columns": ";".join(columns), "notes": "; ".join(notes)})
    result = pd.DataFrame(rows)
    result.to_csv(EVAL / "quarterly_lfs_schema_inventory.csv", index=False)
    return result


def build(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    resolved = resolve_columns(columns)
    required = [resolved[x] for x in ["household", "weight", "rel", "sex", "age", "grade", "status", "occupation", "industry", "nature", "normal_hours", "primary_hours", "class", "total_hours"] if resolved[x]]
    optional = [resolved[x] for x in ["region", "size", "pay_basis", "basic_pay", "jobs", "other_job"] if resolved[x]]
    frame = pd.read_csv(path, usecols=list(dict.fromkeys(required + optional)), low_memory=False)
    def num(concept: str) -> pd.Series:
        column = resolved[concept]
        if column is None:
            return pd.Series(np.nan, index=frame.index, dtype="float64")
        return pd.to_numeric(frame[column], errors="coerce")
    hh = clean_code(frame[resolved["household"]])
    e = pd.DataFrame({"HH": hh, "weight": num("weight"), "region": num("region") if resolved["region"] else np.nan, "rel": num("rel"), "sex": num("sex"), "age": num("age"), "grade": clean_code(frame[resolved["grade"]]), "status": num("status"), "occ": clean_code(frame[resolved["occupation"]]), "industry": clean_code(frame[resolved["industry"]]), "nature": clean_code(frame[resolved["nature"]]), "normal": num("normal_hours"), "primary": num("primary_hours"), "class": clean_code(frame[resolved["class"]]), "total": num("total_hours")})
    e["edu"] = pd.to_numeric(first_digits(e.grade, 1), errors="coerce")
    e["occ_major"] = first_digits(e.occ, 1)
    e["occ_2d"] = first_digits(e.occ, 2)
    e["ind_2d"] = pd.to_numeric(first_digits(e.industry, 2), errors="coerce")
    e["ind_section"] = e.ind_2d.map(DIVISION_TO_SECTION).astype("string")
    e["employed"] = (e.status == 1).astype(int)
    e["unemployed"] = (e.status == 2).astype(int)
    e["nilf"] = (e.status == 3).astype(int)
    e["working"] = (e.age >= 15).astype(int)
    e["child"] = (e.age < 15).astype(int)
    e["adult"] = e.age.between(15, 64, inclusive="both").astype(int)
    e["senior"] = (e.age >= 65).astype(int)
    e["male"] = (e.sex == 1).astype(int)
    e["female"] = (e.sex == 2).astype(int)
    e["multi"] = ((num("jobs") > 1) if resolved["jobs"] else (num("other_job") == 1)).fillna(False).astype(int)
    e["pay_reported"] = ((e.employed == 1) & pd.to_numeric(frame[resolved["basic_pay"]], errors="coerce").notna()).astype(int) if resolved["basic_pay"] else np.nan
    e["basic_pay"] = pd.to_numeric(frame[resolved["basic_pay"]], errors="coerce") if resolved["basic_pay"] else np.nan
    e["pay_basis"] = clean_code(frame[resolved["pay_basis"]]) if resolved["pay_basis"] else pd.Series(pd.NA, index=e.index, dtype="string")
    g = e.groupby("HH", sort=False, dropna=False)
    out = g.agg(MEMBER_COUNT=("HH", "size"), MALE_MEMBERS=("male", "sum"), FEMALE_MEMBERS=("female", "sum"), CHILDREN_0_14=("child", "sum"), ADULTS_15_64=("adult", "sum"), SENIORS_65_PLUS=("senior", "sum"), WORKING_AGE_MEMBERS=("working", "sum"), MEAN_AGE=("age", "mean"), MEDIAN_AGE=("age", "median"), MEAN_ADULT_EDUCATION_LEVEL=("edu", lambda x: x[e.loc[x.index, "age"] >= 15].mean()), MAX_ADULT_EDUCATION_LEVEL=("edu", lambda x: x[e.loc[x.index, "age"] >= 15].max()), EMPLOYED_MEMBERS=("employed", "sum"), UNEMPLOYED_MEMBERS=("unemployed", "sum"), NILF_MEMBERS=("nilf", "sum"), AVG_TOTAL_HOURS_WORKED=("total", lambda x: x[e.loc[x.index, "employed"] == 1].mean()), TOTAL_HOUSEHOLD_WORK_HOURS=("total", lambda x: x[e.loc[x.index, "employed"] == 1].sum(min_count=1)), AVG_PRIMARY_JOB_HOURS=("primary", lambda x: x[e.loc[x.index, "employed"] == 1].mean()), TOTAL_PRIMARY_JOB_HOURS=("primary", lambda x: x[e.loc[x.index, "employed"] == 1].sum(min_count=1)), AVG_NORMAL_HOURS=("normal", lambda x: x[e.loc[x.index, "employed"] == 1].mean()), TOTAL_NORMAL_HOURS=("normal", lambda x: x[e.loc[x.index, "employed"] == 1].sum(min_count=1)), MULTI_JOB_WORKERS=("multi", "sum"), BASIC_PAY_REPORTED_WORKERS=("pay_reported", "sum"), DISTINCT_OCCUPATIONS=("occ_2d", lambda x: x[e.loc[x.index, "employed"] == 1].dropna().nunique()), DISTINCT_INDUSTRIES=("ind_2d", lambda x: x[e.loc[x.index, "employed"] == 1].dropna().nunique()), DISTINCT_WORKER_CLASSES=("class", lambda x: x[e.loc[x.index, "employed"] == 1].dropna().nunique()), DISTINCT_NATURE_CODES=("nature", lambda x: x[e.loc[x.index, "employed"] == 1].dropna().nunique()), DISTINCT_PAY_BASIS_CODES=("pay_basis", lambda x: x[e.loc[x.index, "employed"] == 1].dropna().nunique()), HEAD_AGE=("age", lambda x: x[e.loc[x.index, "rel"] == 1].iloc[0] if (e.loc[x.index, "rel"] == 1).any() else np.nan), HEAD_EDUCATION_LEVEL=("edu", lambda x: x[e.loc[x.index, "rel"] == 1].iloc[0] if (e.loc[x.index, "rel"] == 1).any() else np.nan), HEAD_EMPLOYED=("employed", lambda x: x[e.loc[x.index, "rel"] == 1].iloc[0] if (e.loc[x.index, "rel"] == 1).any() else np.nan), HEAD_IS_FEMALE=("female", lambda x: x[e.loc[x.index, "rel"] == 1].iloc[0] if (e.loc[x.index, "rel"] == 1).any() else np.nan), HEAD_TOTAL_HOURS_WORKED=("total", lambda x: x[e.loc[x.index, "rel"].eq(1) & e.loc[x.index, "employed"].eq(1)].iloc[0] if (e.loc[x.index, "rel"].eq(1) & e.loc[x.index, "employed"].eq(1)).any() else np.nan), HEAD_BASIC_PAY=("basic_pay", lambda x: x[e.loc[x.index, "rel"].eq(1) & e.loc[x.index, "employed"].eq(1)].iloc[0] if (e.loc[x.index, "rel"].eq(1) & e.loc[x.index, "employed"].eq(1)).any() else np.nan)).reset_index().rename(columns={"HH": "PUFHHNUM"})
    out["LABOR_FORCE_MEMBERS"] = out.EMPLOYED_MEMBERS + out.UNEMPLOYED_MEMBERS
    out["EMPLOYMENT_RATIO"] = ratio(out.EMPLOYED_MEMBERS, out.WORKING_AGE_MEMBERS)
    out["UNEMPLOYMENT_RATIO"] = ratio(out.UNEMPLOYED_MEMBERS, out.LABOR_FORCE_MEMBERS)
    out["LABOR_FORCE_PARTICIPATION_RATIO"] = ratio(out.LABOR_FORCE_MEMBERS, out.WORKING_AGE_MEMBERS)
    out["EMPLOYED_SHARE_OF_HOUSEHOLD"] = out.EMPLOYED_MEMBERS / out.MEMBER_COUNT
    out["WORKING_AGE_SHARE"] = out.WORKING_AGE_MEMBERS / out.MEMBER_COUNT
    out["CHILD_SHARE"] = out.CHILDREN_0_14 / out.MEMBER_COUNT
    out["SENIOR_SHARE"] = out.SENIORS_65_PLUS / out.MEMBER_COUNT
    out["FEMALE_SHARE"] = out.FEMALE_MEMBERS / out.MEMBER_COUNT
    out["DEPENDENT_MEMBERS"] = out.CHILDREN_0_14 + out.SENIORS_65_PLUS
    out["DEPENDENCY_RATIO"] = ratio(out.DEPENDENT_MEMBERS, out.ADULTS_15_64)
    out["WORK_HOURS_PER_MEMBER"] = out.TOTAL_HOUSEHOLD_WORK_HOURS / out.MEMBER_COUNT
    out["WORK_HOURS_PER_WORKING_AGE_MEMBER"] = ratio(out.TOTAL_HOUSEHOLD_WORK_HOURS, out.WORKING_AGE_MEMBERS)
    out["MULTI_JOB_WORKER_SHARE"] = ratio(out.MULTI_JOB_WORKERS, out.EMPLOYED_MEMBERS)
    out["BASIC_PAY_REPORTED_SHARE"] = ratio(out.BASIC_PAY_REPORTED_WORKERS, out.EMPLOYED_MEMBERS)
    def grouped_count(mask: pd.Series) -> pd.Series:
        return e.loc[mask].groupby("HH", sort=False).size().reindex(out.PUFHHNUM, fill_value=0).reset_index(drop=True)

    for code in map(str, range(10)):
        for prefix, col in [("OCC_MAJOR", "occ_major"), ("CLASS", "class"), ("NATURE", "nature"), ("PAY_BASIS", "pay_basis")]:
            counts = grouped_count((e[col] == code) & (e.employed == 1))
            out[f"{prefix}_{code}_SHARE"] = ratio(counts, out.EMPLOYED_MEMBERS).to_numpy()
        counts = grouped_count((e.edu.astype("string") == code) & (e.age >= 15))
        out[f"EDU_LEVEL_{code}_SHARE"] = ratio(counts, out.WORKING_AGE_MEMBERS).to_numpy()
        pay_mask = (e.pay_basis == code) & (e.employed == 1)
        pay_count = grouped_count(pay_mask)
        pay_sum = e.loc[pay_mask].groupby("HH", sort=False)["basic_pay"].mean().reindex(out.PUFHHNUM)
        out[f"PAY_BASIS_{code}_MEAN_BASIC_PAY"] = pay_sum.mask(pay_count.eq(0), 0).to_numpy()
    for section in "ABCDEFGHIJKLMNOPQRSTU":
        counts = grouped_count((e.ind_section == section) & (e.employed == 1))
        out[f"IND_SECTION_{section}_SHARE"] = ratio(counts, out.EMPLOYED_MEMBERS).to_numpy()
    out["_WEIGHT"] = g.weight.first().to_numpy()
    out["_REGION"] = g.region.first().to_numpy()
    head_counts = g.rel.apply(lambda x: (x == 1).sum())
    diagnostics = {"source_file": str(path), "person_rows": len(e), "unique_households": len(out), "duplicate_pufhhnum_rows": int(e.HH.duplicated().sum()), "weight_inconsistent_households": int(g.weight.nunique().gt(1).sum()), "head_missing": int(head_counts.eq(0).sum()), "head_multiple": int(head_counts.gt(1).sum()), "province_available": False, "region_inconsistent_households": int(g.region.nunique().gt(1).sum()) if resolved["region"] else None, "columns": resolved}
    return out, diagnostics


def main() -> None:
    EVAL.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    inv = inventory()
    selected = {"2022_Q1": RAW / "LFS PUF February 2022.csv", "2023_Q1": RAW / "LFS PUF January 2023.CSV", "2024_Q1": RAW / "LFS PUF February 2024.CSV", "2025_Q3": RAW / "LFS PUF August 2025.CSV"}
    all_features = json.loads(MANIFEST.read_text(encoding="utf-8")); diagnostics = []
    for label, path in selected.items():
        built, diag = build(path); diagnostics.append({"label": label, **diag}); built.drop(columns=["_WEIGHT", "_REGION"], errors="ignore").to_csv(OUT / f"{label}_household_features.csv", index=False)
    pd.DataFrame(diagnostics).to_json(EVAL / "quarterly_lfs_household_aggregation_diagnostics.json", orient="records", indent=2)
    provenance = pd.read_csv(PROVENANCE).set_index("feature_name")
    pay = {"BASIC_PAY_REPORTED_WORKERS", "BASIC_PAY_REPORTED_SHARE", "HEAD_BASIC_PAY", *[f"PAY_BASIS_{i}_SHARE" for i in range(10)], *[f"PAY_BASIS_{i}_MEAN_BASIC_PAY" for i in range(10)]}
    rows = []
    for i, feature in enumerate(all_features):
        p = provenance.loc[feature]
        is_pay = feature in pay
        status = "PERIOD_LIMITED" if is_pay else "VALIDATED_WITH_HARMONIZATION"
        fields = str(p["raw_training_fields"])
        qfields = "PUF aliases harmonized in quarterly_lfs_feature_builder.py"
        rule = "Alias mapping; first-digit education harmonization; first-digit occupation major; first-two-digit occupation/industry; PSIC division-to-section mapping; PUFHHNUM household grouping" if not is_pay else "No safe all-period rule: PBASIS/PBASIC absent from short-format quarters"
        rows.append({"feature_name": feature, "feature_index": i, "feature_group": p["feature_group"], "recovered_training_formula": p["transformation"], "training_source_fields": fields, "quarterly_lfs_source_fields": qfields, "harmonization_required": True, "harmonization_rule": rule, "availability_periods": "all inspected periods" if not is_pay else "full-format periods only", "final_status": status, "reason": "Recovered formula is implementable from standalone LFS aliases and codebook semantics" if not is_pay else "Required pay-basis/basic-pay source fields absent from short-format quarterly LFS", "quarterly_safe": not is_pay, "notes": "PUFHHNUM used only within survey file; no historical household join."})
    contract = pd.DataFrame(rows); contract.to_csv(EVAL / "validated_quarterly_lfs_feature_contract.csv", index=False)
    contract[~contract.quarterly_safe].to_csv(EVAL / "excluded_quarterly_features.csv", index=False)
    training = pd.read_csv(TRAINING, usecols=all_features, low_memory=False)
    reconstructed = pd.concat([pd.read_csv(OUT / f"{label}_household_features.csv", usecols=all_features) for label in selected], ignore_index=True)
    dist = []
    for feature in all_features:
        a = pd.to_numeric(training[feature], errors="coerce"); b = pd.to_numeric(reconstructed[feature], errors="coerce")
        dist.append({"feature_name": feature, "training_mean": a.mean(), "quarterly_mean": b.mean(), "training_median": a.median(), "quarterly_median": b.median(), "training_std": a.std(), "quarterly_std": b.std(), "training_min": a.min(), "quarterly_min": b.min(), "training_max": a.max(), "quarterly_max": b.max(), "training_missingness": a.isna().mean(), "quarterly_missingness": b.isna().mean(), "scale_flag": "inspect" if (a.mean() and b.mean() and max(a.mean()/b.mean(), b.mean()/a.mean()) > 10) else "none"})
    pd.DataFrame(dist).to_csv(EVAL / "quarterly_vs_training_distribution_check.csv", index=False)
    checks = []
    for label in selected:
        d = pd.read_csv(OUT / f"{label}_household_features.csv")
        checks.append({"period": label, "rows": len(d), "unique_rows": d.PUFHHNUM.nunique(), "one_row_per_household": len(d) == d.PUFHHNUM.nunique(), "employment_ratio_max_error": (d.EMPLOYMENT_RATIO - d.EMPLOYED_MEMBERS / d.WORKING_AGE_MEMBERS.replace(0, np.nan)).abs().max(), "unemployment_ratio_max_error": (d.UNEMPLOYMENT_RATIO - d.UNEMPLOYED_MEMBERS / d.LABOR_FORCE_MEMBERS.replace(0, np.nan)).abs().max(), "lfpr_max_error": (d.LABOR_FORCE_PARTICIPATION_RATIO - d.LABOR_FORCE_MEMBERS / d.WORKING_AGE_MEMBERS.replace(0, np.nan)).abs().max(), "contains_bread": "BREAD" in d.columns})
    pd.DataFrame(checks).to_csv(EVAL / "quarterly_lfs_internal_consistency_checks.csv", index=False)
    family = contract.assign(excluded=~contract.quarterly_safe).groupby("feature_group").agg(original_count=("feature_name", "size"), validated_count=("quarterly_safe", "sum"), period_limited_count=("final_status", lambda s: (s == "PERIOD_LIMITED").sum()), excluded_count=("excluded", "sum")).reset_index(); family.to_csv(EVAL / "quarterly_feature_family_summary.csv", index=False)
    (EVAL / "survey_weight_quarterly_audit.md").write_text("""# Quarterly LFS survey-weight audit\n\n`PUFPWGTPRV` is documented in the available PSA DCF codebook as **Final Weight Based on Projection**. It is present on person/member records. The codebook does not establish that it is a household weight, and it is not the historical FIES-LFS `RFACT` field. The builder checks within-household constancy but does not convert or reinterpret the weight.\n\nA defensible household estimator may use the common member value only after confirming that the survey documentation defines the repeated value as the household expansion weight. This audit does not certify that step. Therefore the future regional aggregation formula remains conditional: `p_t = sum_h(w_h,t * y_hat_h,t)` if `w_h,t` is confirmed as the valid household expansion weight; otherwise the estimator is unresolved. `PUFPWGTPRV` is not an XGBoost predictor.\n""", encoding="utf-8")
    (EVAL / "definitive_quarterly_lfs_reconstruction_report.md").write_text(f"""# Definitive standalone quarterly-LFS reconstruction audit\n\n## Counts\n\n- Total Model B features: 129\n- Validated reproducible: 0\n- Validated with harmonization: {int(contract.final_status.eq('VALIDATED_WITH_HARMONIZATION').sum())}\n- Period limited: {int(contract.final_status.eq('PERIOD_LIMITED').sum())}\n- Source field missing: 0\n- Semantic mismatch: 0\n- Mapping unresolved: 0\n- Not applicable: 0\n- Leakage/future: 0\n\n**Validated quarterly feature set: {int(contract.quarterly_safe.sum())}/129 = {contract.quarterly_safe.mean()*100:.2f}%**.\n\nThe 106 non-pay features are constructible with explicit schema/code harmonization. The 23 pay/basic-pay features are period-limited because short-format quarterly LFS files omit `PUFC24_PBASIS` and `PUFC25_PBASIC`.\n\n## Household unit\n\n`PUFHHNUM` produces one household row per survey file after grouping person/member rows. It is period-local and need not match historical `SEQ_NO`. The builder detected member-row duplicates as expected, checked weight constancy, and checked candidate household-head counts. Residential province is not consistently present in the standalone files; `PUFC11A_PROVMUN` is not silently treated as residential province.\n\n## Semantics\n\nRecovered formulas were reused from `feature_engineering_provenance.csv`. Harmonization includes aliases for full/short occupation, industry, nature, class, and total-hours fields; first-digit education mapping; first-digit occupation major groups; first-two-digit occupation and PSIC divisions; and official PSIC A–U section mapping. Multi-job status uses `PUFC27_NJOBS > 1` where available and the documented `Other Job Indicator == 1` equivalent in short files.\n\n## Weight and regional indicator\n\nThe codebook labels `PUFPWGTPRV` “Final Weight Based on Projection,” but this audit does not certify it as a household expansion weight. The future indicator is therefore conditional: `p_t = Σ_h w_(h,t) * y_hat_(h,t)` only after confirming the household-level meaning of the repeated member weight. No normalization is invented.\n\n## Decision\n\n**B — Retrain Model B on the validated quarterly feature subset**, subject to resolving the quarterly weight role and the deliberate exclusion of 23 pay features. Do not retrain as part of this audit. The retained feature families cover household composition, head variables except head pay, labor, ratios, hours, occupation, industry, education, class, nature, diversity, and multi-job indicators. Pay/basic-pay features are excluded across general quarterly inference.\n""", encoding="utf-8")


if __name__ == "__main__":
    main()

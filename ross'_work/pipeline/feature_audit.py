"""Strict Model B quarterly-LFS feature reproducibility audit.

This is an audit/report generator. It does not retrain, alter the model, or
alter temporal/spatial benchmarking. The classification deliberately records
where the repository lacks the original training feature-engineering script.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "models" / "xgboost_model_features.json"
EVALUATION = ROOT / "evaluation"


def _ranges(prefix: str, n: int) -> list[str]:
    return [f"{prefix}{i}_SHARE" for i in range(n)]


HOUSEHOLD_DERIVED = {
    "MEMBER_COUNT", "MALE_MEMBERS", "FEMALE_MEMBERS", "FEMALE_SHARE",
    "CHILDREN_0_14", "ADULTS_15_64", "SENIORS_65_PLUS", "WORKING_AGE_MEMBERS",
    "MEAN_AGE", "MEDIAN_AGE", "DEPENDENT_MEMBERS", "DEPENDENCY_RATIO",
    "EMPLOYED_SHARE_OF_HOUSEHOLD", "WORKING_AGE_SHARE", "CHILD_SHARE", "SENIOR_SHARE",
    "TOTAL_HOUSEHOLD_WORK_HOURS", "WORK_HOURS_PER_MEMBER",
    "WORK_HOURS_PER_WORKING_AGE_MEMBER", "TOTAL_PRIMARY_JOB_HOURS", "TOTAL_NORMAL_HOURS",
}
MAPPING_DERIVED = set(
    _ranges("OCC_MAJOR_", 10)
    + _ranges("CLASS_", 10)
    + _ranges("NATURE_", 10)
    + _ranges("EDU_LEVEL_", 10)
    + [f"IND_SECTION_{x}_SHARE" for x in "ABCDEFGHIJKLMNOPQRSTU"]
    + [
        "LABOR_FORCE_MEMBERS", "EMPLOYED_MEMBERS", "UNEMPLOYED_MEMBERS", "NILF_MEMBERS",
        "EMPLOYMENT_RATIO", "UNEMPLOYMENT_RATIO", "LABOR_FORCE_PARTICIPATION_RATIO",
        "DISTINCT_OCCUPATIONS", "DISTINCT_INDUSTRIES", "DISTINCT_WORKER_CLASSES",
        "DISTINCT_NATURE_CODES", "DISTINCT_PAY_BASIS_CODES", "MULTI_JOB_WORKERS",
        "MULTI_JOB_WORKER_SHARE",
    ]
)
VERIFY = {
    "MEAN_ADULT_EDUCATION_LEVEL", "MAX_ADULT_EDUCATION_LEVEL", "AVG_TOTAL_HOURS_WORKED",
    "AVG_PRIMARY_JOB_HOURS", "AVG_NORMAL_HOURS", "HEAD_AGE", "HEAD_EDUCATION_LEVEL",
    "HEAD_EMPLOYED", "HEAD_IS_FEMALE", "HEAD_TOTAL_HOURS_WORKED",
}
PAY_BLOCKED = {
    "BASIC_PAY_REPORTED_WORKERS", "BASIC_PAY_REPORTED_SHARE", "HEAD_BASIC_PAY",
    *[f"PAY_BASIS_{i}_SHARE" for i in range(10)],
    *[f"PAY_BASIS_{i}_MEAN_BASIC_PAY" for i in range(10)],
}


def group_for(feature: str) -> str:
    if feature.startswith("OCC_MAJOR_"): return "occupation"
    if feature.startswith("IND_SECTION_"): return "industry"
    if feature.startswith("CLASS_"): return "class of worker"
    if feature.startswith("NATURE_"): return "nature of employment"
    if feature.startswith("PAY_BASIS_") or "BASIC_PAY" in feature: return "pay basis/pay"
    if feature.startswith("EDU_LEVEL_") or "EDUCATION" in feature: return "education"
    if feature.startswith("HEAD_"): return "household head"
    if "HOURS" in feature or "WORK_HOURS" in feature: return "work hours"
    if feature in {"LABOR_FORCE_MEMBERS", "EMPLOYED_MEMBERS", "UNEMPLOYED_MEMBERS", "NILF_MEMBERS", "EMPLOYMENT_RATIO", "UNEMPLOYMENT_RATIO", "LABOR_FORCE_PARTICIPATION_RATIO"}: return "labor-force status"
    if "MULTI_JOB" in feature: return "multiple jobs"
    if feature.startswith("DISTINCT_"): return "distinct coded attributes"
    return "household composition"


def sources_for(feature: str) -> str:
    if feature in PAY_BLOCKED: return "PUFC24_PBASIS/PUFC25_PBASIC (full format only; aliases vary)"
    if feature.startswith("OCC_MAJOR_") or feature == "DISTINCT_OCCUPATIONS": return "PUFC14_PROCC or PUFC13_PROCC; PUFNEWEMPSTAT/worker records"
    if feature.startswith("IND_SECTION_") or feature == "DISTINCT_INDUSTRIES": return "PUFC16_PKB or PUFC15_PKB; PSA/PSIC codebook"
    if feature.startswith("CLASS_") or feature in {"DISTINCT_WORKER_CLASSES"}: return "PUFC23_PCLASS or PUFC21_PCLASS; DCF class-of-worker mapping"
    if feature.startswith("NATURE_") or feature == "DISTINCT_NATURE_CODES": return "PUFC17_NATEM or PUFC16_NATEM"
    if feature.startswith("EDU_LEVEL_") or "EDUCATION" in feature: return "PUFC07_GRADE; DCF education mapping"
    if feature.startswith("HEAD_"): return "PUFC03_REL, PUF C04_SEX, PUFC05_AGE, education, work and hours fields"
    if "HOURS" in feature or "WORK_HOURS" in feature: return "PUFC18_PHOURS/PUFC17_PHOURS and PUFC28_THOURS/PUFC23_THOURS"
    if feature in {"LABOR_FORCE_MEMBERS", "EMPLOYED_MEMBERS", "UNEMPLOYED_MEMBERS", "NILF_MEMBERS", "EMPLOYMENT_RATIO", "UNEMPLOYMENT_RATIO", "LABOR_FORCE_PARTICIPATION_RATIO"}: return "PUFNEWEMPSTAT or work/status aliases"
    if feature in {"MULTI_JOB_WORKERS", "MULTI_JOB_WORKER_SHARE"}: return "PUFC12_JOB/PUFC10_JOB and PUF C27_NJOBS where available"
    return "PUFHHNUM, PUF C01_LNO, PUF C04_SEX, PUF C05_AGE"


def transformation_for(feature: str, status: str) -> str:
    if feature == "MEMBER_COUNT": return "group by PUFHHNUM; count member rows"
    if feature == "MALE_MEMBERS": return "group by household; count sex=male"
    if feature == "FEMALE_MEMBERS": return "group by household; count sex=female"
    if feature == "FEMALE_SHARE": return "female members / member count"
    if feature == "CHILDREN_0_14": return "count members with age 0–14"
    if feature == "ADULTS_15_64": return "count members with age 15–64"
    if feature == "SENIORS_65_PLUS": return "count members age 65+"
    if feature == "WORKING_AGE_MEMBERS": return "count members age 15–64"
    if feature == "MEAN_AGE": return "household mean of member age"
    if feature == "MEDIAN_AGE": return "household median of member age"
    if feature == "DEPENDENT_MEMBERS": return "children plus seniors; exact training definition not verified"
    if feature == "DEPENDENCY_RATIO": return "dependents / working-age members; formula_not_verified"
    if feature == "TOTAL_HOUSEHOLD_WORK_HOURS": return "sum member total-hours field within household"
    if feature == "TOTAL_PRIMARY_JOB_HOURS": return "sum member primary-job hours within household"
    if feature == "TOTAL_NORMAL_HOURS": return "sum member normal-hours field within household"
    if feature == "WORK_HOURS_PER_MEMBER": return "total household work hours / member count"
    if feature == "WORK_HOURS_PER_WORKING_AGE_MEMBER": return "total work hours / working-age members"
    if feature == "EMPLOYED_SHARE_OF_HOUSEHOLD": return "employed members / member count"
    if feature == "WORKING_AGE_SHARE": return "working-age members / member count"
    if feature == "CHILD_SHARE": return "children / member count"
    if feature == "SENIOR_SHARE": return "seniors / member count"
    if feature in MAPPING_DERIVED: return "aggregate/filter raw member records using documented codebook mapping; formula_not_verified"
    if status == "E": return "not generally available across all quarterly raw schemas; pay fields absent in short-format files"
    return "formula_not_verified; plausible raw source exists, but original preprocessing implementation is absent"


def classify(feature: str) -> str:
    if feature in PAY_BLOCKED: return "E_NOT_REPRODUCIBLE_FROM_QUARTERLY_LFS"
    if feature in VERIFY: return "D_POSSIBLY_REPRODUCIBLE_NEEDS_VERIFICATION"
    if feature in MAPPING_DERIVED: return "C_REPRODUCIBLE_WITH_EXISTING_MAPPING_CODEBOOK"
    if feature in HOUSEHOLD_DERIVED: return "B_DERIVABLE_FROM_LFS"
    return "D_POSSIBLY_REPRODUCIBLE_NEEDS_VERIFICATION"


def main() -> None:
    features = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for index, feature in enumerate(features):
        status = classify(feature)
        category_letter = status[0]
        rows.append({
            "feature_name": feature,
            "feature_index": index,
            "feature_group": group_for(feature),
            "reproducibility_status": status,
            "raw_lfs_source_columns": sources_for(feature),
            "training_source_columns": "UNVERIFIED: original feature-engineering script is not present in inspected repository",
            "transformation": transformation_for(feature, status),
            "statistical_unit": "household after grouping person/member rows by PUFHHNUM",
            "mapping_required": category_letter in {"C", "D"},
            "mapping_source": "2023 monthly DCF/codebook and PSA occupation/industry/classification documentation" if category_letter in {"C", "D"} else "none",
            "available_each_quarter": "no: short-format quarters lack pay fields" if category_letter == "E" else "raw source present, but schemas require harmonization and representative-month rule",
            "future_information_required": False,
            "fies_only_dependency": False,
            "confidence": "high" if category_letter == "B" else "medium" if category_letter == "C" else "low" if category_letter == "D" else "high (unavailable)",
            "formula_verified": False if category_letter in {"C", "D", "E"} else True,
            "notes": "No final engineered feature column exists in raw LFS. Household IDs and survey weights exist. Original training transformation code was not found." if category_letter != "E" else "Present in full-format months, but not defensibly available for every quarterly raw schema in the repository; 2022 Q1 and 2025 Q3 are material examples.",
            "feature_source": "LFS-derived likely; training provenance unverified",
        })
    df = pd.DataFrame(rows)
    EVALUATION.mkdir(parents=True, exist_ok=True)
    df.to_csv(EVALUATION / "model_b_lfs_feature_compatibility.csv", index=False)

    counts = Counter(df["reproducibility_status"])
    group_rows = []
    for group, g in df.groupby("feature_group", sort=True):
        strict = g["reproducibility_status"].str.startswith(tuple(["A_", "B_", "C_"])).sum()
        uncertain = g["reproducibility_status"].str.startswith("D_").sum()
        unavailable = g["reproducibility_status"].str.startswith("E_").sum()
        leakage = g["reproducibility_status"].str.startswith("F_").sum()
        group_rows.append({"feature_group": group, "total_features": len(g), "strict_category_count": int(strict), "uncertain": int(uncertain), "unavailable": int(unavailable), "leakage_invalid": int(leakage)})
    pd.DataFrame(group_rows).to_csv(EVALUATION / "model_b_lfs_feature_group_summary.csv", index=False)

    source_summary = pd.DataFrame([
        {"feature_source": "LFS-derived likely; training provenance unverified", "count": len(df), "note": "No original preprocessing script was found; BREAD is not in the 129-feature manifest."},
        {"feature_source": "FIES-only identified predictor", "count": 0, "note": "No manifest feature contains BREAD or an identified FIES target."},
        {"feature_source": "joint/unknown", "count": 0, "note": "No additional source class could be proven from available artifacts."},
    ])
    source_summary.to_csv(EVALUATION / "model_b_lfs_feature_source_summary.csv", index=False)

    strict = sum(counts[s] for s in counts if s[:2] in {"A_", "B_", "C_"})
    potential = strict + sum(counts[s] for s in counts if s.startswith("D_"))
    md = f"""# Model B raw quarterly-LFS feature audit\n\nGenerated from `models/xgboost_model_features.json` ({len(features)} features). This report is an audit artifact; it does not retrain or modify the model or benchmarking code.\n\n## Counts\n\n- A directly reproducible: {counts.get('A_DIRECTLY_REPRODUCIBLE', 0)}\n- B derivable from LFS: {counts.get('B_DERIVABLE_FROM_LFS', 0)}\n- C reproducible with existing mapping/codebook: {counts.get('C_REPRODUCIBLE_WITH_EXISTING_MAPPING_CODEBOOK', 0)}\n- D possibly reproducible, needs verification: {counts.get('D_POSSIBLY_REPRODUCIBLE_NEEDS_VERIFICATION', 0)}\n- E not reproducible from quarterly LFS: {counts.get('E_NOT_REPRODUCIBLE_FROM_QUARTERLY_LFS', 0)}\n- F leakage/invalid: {counts.get('F_LEAKAGE_INVALID_FOR_CURRENT_INFERENCE', 0)}\n\nRequested category arithmetic gives **strictly reproducible = {strict}/129 ({strict / len(features) * 100:.2f}%)** and **potentially reproducible = {potential}/129 ({potential / len(features) * 100:.2f}%)**. This is an information-availability count, not a claim that the C formulas are production-ready: the original feature-engineering code was not found, so all C transformations remain formula-unverified.\n\n## Unit and provenance findings\n\nTraining rows are household-level (`HOUSEHOLD_ID`, one row per household). Raw LFS files are person/member-level and contain `PUFHHNUM`, so household grouping is structurally possible. The raw household IDs are survey identifiers and are not longitudinal links to FIES household IDs.\n\nThe raw LFS contains household identifiers, member demographics, work/status fields, hours, occupation, industry, nature, class, education, and survey weight fields. 2023 DCF codebooks are available. However, monthly formats are not stable: short-format files omit pay/basic-pay fields and some normal-hours fields. The repository also lacks the original preprocessing script that generated the 129 training features and lacks raw 2018 quarterly LFS microdata.\n\nNo feature in the manifest is `BREAD`, and no FIES-only predictor or future-quarter dependency was identified. Survey weights are not among the 129 model predictors; their training aggregation/evaluation use could not be verified from executable preprocessing code.\n\n## Recommendation\n\n**UNDETERMINED — do not retain Model B for quarterly inference yet.** The raw information is substantially present, but exact training-equivalent transformations, quarter-selection rules, and cross-format harmonization are not proven. The pay block is not generally available in every quarterly raw schema. This audit does not retrain or alter any runtime.\n\nSee `model_b_lfs_feature_compatibility.csv`, `model_b_lfs_feature_group_summary.csv`, and `model_b_lfs_feature_source_summary.csv`.\n"""
    (EVALUATION / "model_b_lfs_feature_audit.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()

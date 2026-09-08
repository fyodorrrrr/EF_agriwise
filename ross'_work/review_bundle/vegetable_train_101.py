"""Train the quarterly-safe XGBoost model for household vegetable expenditure."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from .train_quarterly_101 import PARAMETERS, metrics

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
DATA_ROOT = REPO_ROOT / "data" / "processed" / "demand"
RAW_ROOT = REPO_ROOT / "data" / "raw" / "PHL-PSA-FIES-LFS"
ARTIFACT_ROOT = PACKAGE_ROOT / "artifacts"
TRAIN_2018 = DATA_ROOT / "fies_lfs" / "fies_lfs_2018_harmonized_psic_training_table.csv"
TRAIN_2023 = DATA_ROOT / "fies_lfs" / "fies_lfs_2023_training_table.csv"
CONTRACT = DATA_ROOT / "evaluation" / "validated_quarterly_lfs_feature_contract.csv"
RAW_2018 = RAW_ROOT / "PHL-PSA-FIES-LFS-2018-PUF" / "FIES-LFS PUF 2018 Household Summary.CSV"
RAW_2023 = RAW_ROOT / "FIES-LFS-houseHoldSummary.CSV"
Q3 = (
    DATA_ROOT
    / "outputs"
    / "quarterly_lfs_feature_reconstruction"
    / "2025_Q3_household_features.csv"
)
MODEL = ARTIFACT_ROOT / "xgboost_vegetable_quarterly_101.json"
FEATURES_OUT = ARTIFACT_ROOT / "xgboost_vegetable_quarterly_101_features.json"
PARAMS_OUT = ARTIFACT_ROOT / "xgboost_vegetable_quarterly_101_parameters.json"
HELDOUT_OUT = DATA_ROOT / "evaluation" / "vegetable_101_heldout_predictions.csv"
REPORT = DATA_ROOT / "evaluation" / "vegetable_101_model_report.md"
Q3_OUT = DATA_ROOT / "outputs" / "2025_Q3_household_predictions_vegetable_101.csv"


def attach_vegetable_target(
    training: pd.DataFrame, raw_summary_path: Path, raw_household_id: str
) -> pd.DataFrame:
    """Attach raw FIES `VEG` expenditure to its prepared feature row."""
    target = pd.read_csv(raw_summary_path, usecols=[raw_household_id, "VEG"], low_memory=False)
    if target[raw_household_id].duplicated().any():
        raise RuntimeError(f"Duplicate household IDs in {raw_summary_path}")
    result = training.drop(columns=["BREAD"]).merge(
        target,
        left_on="HOUSEHOLD_ID",
        right_on=raw_household_id,
        how="left",
        validate="one_to_one",
    )
    result = result.drop(columns=[raw_household_id])
    if result["VEG"].isna().any() or (result["VEG"] < 0).any():
        raise RuntimeError("Vegetable target alignment is incomplete or invalid")
    return result


def main() -> None:
    contract = pd.read_csv(CONTRACT)
    features = contract.loc[contract["quarterly_safe"].eq(True), "feature_name"].tolist()
    if len(features) != 101:
        raise RuntimeError(f"Expected exactly 101 quarterly-safe features; found {len(features)}")
    if {"BREAD", "VEG", "SURVEY_WEIGHT"}.intersection(features):
        raise RuntimeError("A target or survey weight was included in predictors")

    df_2018 = attach_vegetable_target(
        pd.read_csv(TRAIN_2018, low_memory=False), RAW_2018, "SEQUENCE_NO"
    )
    df_2023 = attach_vegetable_target(pd.read_csv(TRAIN_2023, low_memory=False), RAW_2023, "SEQ_NO")
    missing = [feature for feature in features if feature not in df_2018 or feature not in df_2023]
    if missing:
        raise RuntimeError(f"Training features missing: {missing}")

    indices = np.arange(len(df_2023))
    train_idx, test_idx = train_test_split(indices, test_size=0.20, random_state=42, shuffle=True)
    train_2023 = df_2023.iloc[train_idx].copy()
    test_2023 = df_2023.iloc[test_idx].copy()
    train = pd.concat([df_2018, train_2023], ignore_index=True)

    model = XGBRegressor(**PARAMETERS)
    model.fit(train[features], train["VEG"], sample_weight=train["SURVEY_WEIGHT"])
    heldout_predictions = model.predict(test_2023[features])
    evaluation = metrics(
        test_2023["VEG"].to_numpy(),
        heldout_predictions,
        test_2023["SURVEY_WEIGHT"].to_numpy(),
        len(train),
    )

    model.save_model(MODEL)
    FEATURES_OUT.write_text(json.dumps(features, indent=2), encoding="utf-8")
    PARAMS_OUT.write_text(json.dumps(PARAMETERS, indent=2), encoding="utf-8")
    reloaded = XGBRegressor()
    reloaded.load_model(MODEL)
    if reloaded.get_booster().feature_names != features:
        raise RuntimeError("Saved model feature order does not match the saved manifest")

    heldout = pd.DataFrame(
        {
            "HOUSEHOLD_ID": test_2023["HOUSEHOLD_ID"],
            "ACTUAL_VEG": test_2023["VEG"],
            "PREDICTED_VEG": heldout_predictions,
            "SURVEY_WEIGHT": test_2023["SURVEY_WEIGHT"],
        }
    )
    heldout.to_csv(HELDOUT_OUT, index=False)

    q3 = pd.read_csv(Q3, low_memory=False)
    missing_q3 = [feature for feature in features if feature not in q3]
    if missing_q3:
        raise RuntimeError(f"2025 Q3 features missing: {missing_q3}")
    q3_predictions = reloaded.predict(q3[features])
    if not np.isfinite(q3_predictions).all():
        raise RuntimeError("2025 Q3 produced non-finite vegetable predictions")
    pd.DataFrame(
        {
            "year": 2025,
            "quarter": 3,
            "PUFHHNUM": q3["PUFHHNUM"],
            "predicted_vegetable_expenditure": q3_predictions,
        }
    ).to_csv(Q3_OUT, index=False)

    REPORT.write_text(
        f"""# Quarterly 101-feature vegetable-expenditure model

The target is raw FIES household-summary `VEG` expenditure. Training uses the recovered
2018 rows plus the non-held-out 2023 split (`test_size=0.20`, `random_state=42`).
`SURVEY_WEIGHT` is used only as XGBoost `sample_weight`; it is not a predictor.

## Dataset

- Features: {len(features)}
- Model-training households: {len(train):,}
- Held-out 2023 households: {len(test_2023):,}
- 2018 households: {len(df_2018):,}
- Non-held-out 2023 households: {len(train_2023):,}

## Held-out evaluation

{json.dumps(evaluation, indent=2)}

## Quarterly inference

2025 Q3 inference produced {len(q3_predictions):,} household vegetable-expenditure
predictions with finite outputs and exact 101-feature alignment. These are household
`VEG` expenditure predictions, not regional vegetable-demand estimates.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

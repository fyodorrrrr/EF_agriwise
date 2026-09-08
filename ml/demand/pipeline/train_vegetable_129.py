"""Train a vegetable-expenditure model on the full bread-style 129-feature contract."""

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
ARTIFACT_ROOT = PACKAGE_ROOT / "artifacts"
TRAIN_ROOT = DATA_ROOT / "fies_lfs" / "vegetable"
TRAIN_2018 = TRAIN_ROOT / "fies_lfs_2018_vegetable_training_table.csv"
TRAIN_2023 = TRAIN_ROOT / "fies_lfs_2023_vegetable_training_table.csv"
FEATURES = ARTIFACT_ROOT / "xgboost_model_features.json"
MODEL = ARTIFACT_ROOT / "xgboost_vegetable_full_129.json"
FEATURES_OUT = ARTIFACT_ROOT / "xgboost_vegetable_full_129_features.json"
PARAMS_OUT = ARTIFACT_ROOT / "xgboost_vegetable_full_129_parameters.json"
HELDOUT_OUT = DATA_ROOT / "evaluation" / "vegetable_full_129_heldout_predictions.csv"
REPORT = DATA_ROOT / "evaluation" / "vegetable_full_129_model_report.md"


def main() -> None:
    features = json.loads(FEATURES.read_text(encoding="utf-8"))
    if len(features) != 129 or {"BREAD", "VEG", "SURVEY_WEIGHT"}.intersection(features):
        raise RuntimeError("The full feature contract must contain 129 predictor-only features")

    train_2018 = pd.read_csv(TRAIN_2018, low_memory=False)
    train_2023 = pd.read_csv(TRAIN_2023, low_memory=False)
    missing = [
        feature for feature in features if feature not in train_2018 or feature not in train_2023
    ]
    if missing:
        raise RuntimeError(f"Training features missing: {missing}")

    indices = np.arange(len(train_2023))
    train_indices, test_indices = train_test_split(
        indices, test_size=0.20, random_state=42, shuffle=True
    )
    train = pd.concat([train_2018, train_2023.iloc[train_indices]], ignore_index=True)
    heldout = train_2023.iloc[test_indices].copy()

    model = XGBRegressor(**PARAMETERS)
    model.fit(train[features], train["VEG"], sample_weight=train["SURVEY_WEIGHT"])
    predictions = model.predict(heldout[features])
    evaluation = metrics(
        heldout["VEG"].to_numpy(),
        predictions,
        heldout["SURVEY_WEIGHT"].to_numpy(),
        len(train),
    )

    model.save_model(MODEL)
    FEATURES_OUT.write_text(json.dumps(features, indent=2), encoding="utf-8")
    PARAMS_OUT.write_text(json.dumps(PARAMETERS, indent=2), encoding="utf-8")
    reloaded = XGBRegressor()
    reloaded.load_model(MODEL)
    if reloaded.get_booster().feature_names != features:
        raise RuntimeError("Saved model feature order does not match the full feature contract")

    pd.DataFrame(
        {
            "HOUSEHOLD_ID": heldout["HOUSEHOLD_ID"],
            "ACTUAL_VEG": heldout["VEG"],
            "PREDICTED_VEG": predictions,
            "SURVEY_WEIGHT": heldout["SURVEY_WEIGHT"],
        }
    ).to_csv(HELDOUT_OUT, index=False)

    REPORT.write_text(
        f"""# Full 129-feature vegetable-expenditure model

This model uses the exact full feature preprocessing used by the bread Model B training
tables. The only substituted field is the target: raw FIES `BREAD` is replaced by aligned
raw FIES `VEG` expenditure. Training uses the 2018 rows and the non-held-out 2023 split
(`test_size=0.20`, `random_state=42`), with `SURVEY_WEIGHT` as XGBoost `sample_weight`.

## Dataset

- Features: {len(features)}
- Model-training households: {len(train):,}
- Held-out 2023 households: {len(heldout):,}

## Held-out evaluation

{json.dumps(evaluation, indent=2)}

## Quarterly limitation

This full contract includes 28 pay/basic-pay and hours features unavailable in general
quarterly LFS files. It is therefore an evaluation model and must not produce quarterly
inference until an equivalent quarterly feature source exists.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

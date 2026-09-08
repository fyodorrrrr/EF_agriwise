import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
DATA_ROOT = REPO_ROOT / "data" / "processed" / "demand"
ARTIFACT_ROOT = PACKAGE_ROOT / "artifacts"


def test_full_vegetable_preprocessing_preserves_bread_feature_schema():
    bread = pd.read_csv(
        DATA_ROOT / "fies_lfs" / "fies_lfs_2023_training_table.csv", nrows=1
    ).columns.tolist()
    vegetable = pd.read_csv(
        DATA_ROOT / "fies_lfs" / "vegetable" / "fies_lfs_2023_vegetable_training_table.csv",
        nrows=1,
    ).columns.tolist()
    assert vegetable == [column for column in bread if column != "BREAD"] + ["VEG"]


def test_full_vegetable_model_uses_the_129_feature_contract():
    features = json.loads(
        (ARTIFACT_ROOT / "xgboost_vegetable_full_129_features.json").read_text()
    )
    assert len(features) == 129
    assert {"BREAD", "VEG", "SURVEY_WEIGHT"}.isdisjoint(features)

    model = XGBRegressor()
    model.load_model(ARTIFACT_ROOT / "xgboost_vegetable_full_129.json")
    assert model.get_booster().feature_names == features

    heldout = pd.read_csv(DATA_ROOT / "evaluation" / "vegetable_full_129_heldout_predictions.csv")
    assert len(heldout) == 1632
    assert np.isfinite(heldout[["ACTUAL_VEG", "PREDICTED_VEG"]].to_numpy()).all()

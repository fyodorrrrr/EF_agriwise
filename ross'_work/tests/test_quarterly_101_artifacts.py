import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor


ROOT = Path(__file__).resolve().parents[1]


def test_quarterly_101_artifacts_align_and_are_finite():
    contract = pd.read_csv(ROOT / "evaluation/validated_quarterly_lfs_feature_contract.csv")
    features = json.loads((ROOT / "models/xgboost_model_b_quarterly_101_features.json").read_text())
    safe = contract.loc[contract["quarterly_safe"].eq(True), "feature_name"].tolist()
    assert len(safe) == 101
    assert features == safe
    assert "BREAD" not in features
    assert "SURVEY_WEIGHT" not in features

    model = XGBRegressor()
    model.load_model(ROOT / "models/xgboost_model_b_quarterly_101.json")
    assert model.get_booster().feature_names == features

    q3 = pd.read_csv(ROOT / "outputs/2025_Q3_household_predictions_101.csv")
    assert len(q3) == q3["PUFHHNUM"].nunique()
    assert np.isfinite(q3["predicted_bread_expenditure"]).all()

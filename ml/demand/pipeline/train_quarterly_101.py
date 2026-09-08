"""Fast isolated retraining of Model B on the validated quarterly-safe contract."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
DATA_ROOT = REPO_ROOT / "data" / "processed" / "demand"
ARTIFACT_ROOT = PACKAGE_ROOT / "artifacts"
TRAIN_2018 = DATA_ROOT / "fies_lfs" / "fies_lfs_2018_harmonized_psic_training_table.csv"
TRAIN_2023 = DATA_ROOT / "fies_lfs" / "fies_lfs_2023_training_table.csv"
CONTRACT = DATA_ROOT / "evaluation" / "validated_quarterly_lfs_feature_contract.csv"
ORIGINAL_PREDICTIONS = ARTIFACT_ROOT / "xgboost_heldout_2023_predictions.csv"
Q3 = DATA_ROOT / "outputs" / "quarterly_lfs_feature_reconstruction" / "2025_Q3_household_features.csv"
MODEL = ARTIFACT_ROOT / "xgboost_model_b_quarterly_101.json"
FEATURES_OUT = ARTIFACT_ROOT / "xgboost_model_b_quarterly_101_features.json"
PARAMS_OUT = ARTIFACT_ROOT / "xgboost_model_b_quarterly_101_parameters.json"
COMPARISON = DATA_ROOT / "evaluation" / "quarterly_101_model_comparison.csv"
REPORT = DATA_ROOT / "evaluation" / "quarterly_101_model_report.md"
Q3_OUT = DATA_ROOT / "outputs" / "2025_Q3_household_predictions_101.csv"

PARAMETERS = {
    "n_estimators": 900,
    "learning_rate": 0.01,
    "max_depth": 2,
    "min_child_weight": 12,
    "subsample": 0.65,
    "colsample_bytree": 0.50,
    "gamma": 0.05,
    "reg_alpha": 0.50,
    "reg_lambda": 5.0,
    "objective": "reg:squarederror",
    "random_state": 42,
    "n_jobs": -1,
}


def metrics(y: np.ndarray, pred: np.ndarray, weights: np.ndarray, train_rows: int) -> dict[str, float | int]:
    actual_mean = float(np.average(y, weights=weights))
    weighted_mae = float(mean_absolute_error(y, pred, sample_weight=weights))
    weighted_rmse = float(np.sqrt(mean_squared_error(y, pred, sample_weight=weights)))
    actual_total = float(np.sum(y * weights))
    predicted_total = float(np.sum(pred * weights))
    return {
        "training_households": int(train_rows), "heldout_households": int(len(y)),
        "r2": float(r2_score(y, pred, sample_weight=weights)), "mae": weighted_mae,
        "rmse": weighted_rmse, "normalized_mae_percent": float(weighted_mae / actual_mean * 100),
        "aggregate_bias_percent": float((predicted_total - actual_total) / actual_total * 100),
        "target_mean": actual_mean, "prediction_mean": float(np.average(pred, weights=weights)),
        "minimum_prediction": float(np.min(pred)), "maximum_prediction": float(np.max(pred)),
        "negative_predictions": int((pred < 0).sum()), "nonfinite_predictions": int((~np.isfinite(pred)).sum()),
    }


def main() -> None:
    contract = pd.read_csv(CONTRACT)
    features = contract.loc[contract["quarterly_safe"].eq(True), "feature_name"].tolist()
    if len(features) != 101:
        raise RuntimeError(f"Expected exactly 101 quarterly-safe features; found {len(features)}")
    if {"BREAD", "SURVEY_WEIGHT"}.intersection(features):
        raise RuntimeError("Target or survey weight was included in predictors")
    excluded = set(contract.loc[~contract["quarterly_safe"].eq(True), "feature_name"])
    if excluded.intersection(features):
        raise RuntimeError("Excluded contract features were included")

    df_2018 = pd.read_csv(TRAIN_2018, low_memory=False)
    df_2023 = pd.read_csv(TRAIN_2023, low_memory=False)
    missing = [f for f in features if f not in df_2018.columns or f not in df_2023.columns]
    if missing:
        raise RuntimeError(f"Training features missing: {missing}")
    df_2023 = df_2023.reset_index(drop=True)
    df_2018 = df_2018.reset_index(drop=True)
    indices = np.arange(len(df_2023))
    train_idx, test_idx = train_test_split(indices, test_size=0.20, random_state=42, shuffle=True)
    train_2023 = df_2023.iloc[train_idx].copy()
    test_2023 = df_2023.iloc[test_idx].copy()
    train_b = pd.concat([df_2018, train_2023], ignore_index=True)

    model = XGBRegressor(**PARAMETERS)
    model.fit(train_b[features], train_b["BREAD"], sample_weight=train_b["SURVEY_WEIGHT"])
    pred = model.predict(test_2023[features])
    new_metrics = metrics(test_2023["BREAD"].to_numpy(), pred, test_2023["SURVEY_WEIGHT"].to_numpy(), len(train_b))

    old = pd.read_csv(ORIGINAL_PREDICTIONS)
    if len(old) != len(test_2023):
        raise RuntimeError("Original held-out prediction artifact does not match the recovered split size")
    old_metrics = metrics(old["ACTUAL_BREAD"].to_numpy(), old["PREDICTED_MODEL_B"].to_numpy(), old["SURVEY_WEIGHT"].to_numpy(), len(train_b))
    rows = [{"metric": label, "original_129_feature_model": old_metrics[key], "new_101_feature_model": new_metrics[key], "difference": new_metrics[key] - old_metrics[key]} for key, label in [("r2", "R2"), ("mae", "MAE"), ("rmse", "RMSE"), ("normalized_mae_percent", "normalized_MAE_percent"), ("aggregate_bias_percent", "aggregate_bias_percent")]]
    pd.DataFrame(rows).to_csv(COMPARISON, index=False)

    model.save_model(MODEL)
    FEATURES_OUT.write_text(json.dumps(features, indent=2), encoding="utf-8")
    PARAMS_OUT.write_text(json.dumps(PARAMETERS, indent=2), encoding="utf-8")
    reloaded = XGBRegressor()
    reloaded.load_model(MODEL)
    if reloaded.get_booster().feature_names != features:
        raise RuntimeError("Saved model feature order does not match the saved manifest")

    q3 = pd.read_csv(Q3, low_memory=False)
    missing_q3 = [f for f in features if f not in q3.columns]
    if missing_q3:
        raise RuntimeError(f"2025 Q3 features missing: {missing_q3}")
    q3_pred = reloaded.predict(q3[features])
    if not np.isfinite(q3_pred).all():
        raise RuntimeError("2025 Q3 produced non-finite predictions")
    pd.DataFrame({"year": 2025, "quarter": 3, "PUFHHNUM": q3["PUFHHNUM"], "predicted_bread_expenditure": q3_pred}).to_csv(Q3_OUT, index=False)

    report = f"""# Quarterly 101-feature Model B retraining

Training used the recovered 2018 rows plus the exact recovered non-held-out 2023 split (`train_test_split`, `test_size=0.20`, `random_state=42`). `SURVEY_WEIGHT` was used only as XGBoost `sample_weight`; it was not a predictor. No PUFPWGTPRV aggregation, Denton benchmarking, or spatial reconciliation was performed.

## Dataset

- Features: {len(features)}
- Model B training households: {len(train_b):,}
- Held-out 2023 households: {len(test_2023):,}
- 2018 households: {len(df_2018):,}
- 2023 training households: {len(train_2023):,}

## Comparison

{pd.DataFrame(rows).to_string(index=False)}

## New-model sanity check

{json.dumps(new_metrics, indent=2)}

## Original-model sanity check

{json.dumps(old_metrics, indent=2)}

## Quarterly inference

2025 Q3 inference produced {len(q3_pred):,} household predictions with finite outputs and exact 101-feature alignment. These are household BREAD-expenditure predictions, not regional demand estimates.
"""
    REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()

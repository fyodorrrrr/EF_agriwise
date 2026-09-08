"""Model B feature-contract validation and inference boundary."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


class FeatureContractError(ValueError):
    """Raised when an inference table cannot satisfy Model B's feature contract."""


class ModelBInference:
    """Load Model B and refuse unsupported LFS-to-household transformations."""

    def __init__(self, model_path: Path, feature_manifest_path: Path):
        self.model_path = model_path.resolve()
        self.feature_manifest_path = feature_manifest_path.resolve()
        if not self.model_path.is_file() or not self.feature_manifest_path.is_file():
            raise FeatureContractError("Model B artifact or feature manifest is missing")
        self.features = json.loads(self.feature_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(self.features, list) or not self.features or not all(
            isinstance(value, str) for value in self.features
        ):
            raise FeatureContractError("Model B feature manifest is invalid")

    def align_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return exactly the manifest columns, preserving saved feature order."""
        missing = sorted(set(self.features).difference(frame.columns))
        if missing:
            raise FeatureContractError(
                "inference table cannot satisfy Model B feature contract; missing "
                f"{len(missing)} features: {', '.join(missing)}"
            )
        if "BREAD" in self.features:
            raise FeatureContractError("BREAD is a target and cannot be an inference feature")
        aligned = frame.loc[:, self.features].copy()
        for column in self.features:
            aligned[column] = pd.to_numeric(aligned[column], errors="raise")
        if not np.isfinite(aligned.to_numpy(dtype=float)).all():
            raise FeatureContractError("Model B inference features contain NaN or infinite values")
        return aligned

    def predict(self, feature_rows: pd.DataFrame) -> np.ndarray:
        """Run Model B only after an exact feature-contract check."""
        aligned = self.align_features(feature_rows)
        try:
            import xgboost as xgb
        except ImportError as exc:
            raise FeatureContractError("xgboost is required to load Model B") from exc
        booster = xgb.Booster()
        booster.load_model(self.model_path)
        predictions = np.asarray(
            booster.predict(xgb.DMatrix(aligned, feature_names=self.features)), dtype=float
        )
        if not np.isfinite(predictions).all() or (predictions < 0).any():
            raise FeatureContractError("Model B produced invalid demand indicators")
        return predictions

    def predict_from_quarterly_lfs(self, quarterly_lfs: pd.DataFrame) -> pd.DataFrame:
        """Reject the current 7-column regional table rather than inventing features."""
        try:
            aligned = self.align_features(quarterly_lfs)
        except FeatureContractError as exc:
            raise FeatureContractError(
                "The available quarterly LFS table cannot be mapped to Model B. "
                "It contains regional indicators, while Model B requires household-level "
                f"features ({len(self.features)} expected). No implicit aggregation or "
                f"feature fabrication is allowed. Original error: {exc}"
            ) from exc
        predictions = self.predict(aligned)
        result = quarterly_lfs[["YEAR", "QUARTER"]].copy()
        result["raw_xgb_indicator"] = predictions
        result["model_name"] = "xgboost_model_b_2018_2023"
        result["feature_source"] = "quarterly_lfs"
        return result

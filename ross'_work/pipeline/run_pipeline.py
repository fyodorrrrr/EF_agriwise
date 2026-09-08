"""Command-line orchestration for the isolated demand pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .denton import BenchmarkMetadata, proportional_denton
from .inference import ModelBInference
from .spatial import reconcile_spatial


ROOT = Path(__file__).resolve().parents[1]


def run_from_valid_model_rows(
    model_rows: pd.DataFrame,
    benchmarks: dict[int, BenchmarkMetadata],
    *,
    output_root: Path = ROOT / "outputs",
) -> dict[str, pd.DataFrame]:
    """Run inference, Denton, and spatial reconciliation for valid model rows.

    ``model_rows`` must contain ``year``, ``quarter``, and every one of the
    129 saved Model B features. This is intentionally separate from the
    regional seven-column LFS adapter, which cannot satisfy that contract.
    """
    model = ModelBInference(
        ROOT / "models/xgboost_model_b_2018_2023.json",
        ROOT / "models/xgboost_model_features.json",
    )
    required = {"year", "quarter"}.union(model.features)
    missing = sorted(required.difference(model_rows.columns))
    if missing:
        raise ValueError(f"valid Model B rows are missing columns: {', '.join(missing)}")
    raw = model_rows[["year", "quarter"]].copy()
    raw["raw_xgb_indicator"] = model.predict(model_rows[model.features])
    raw["model_name"] = "xgboost_model_b_2018_2023"
    raw["feature_source"] = "validated_quarterly_model_rows"
    denton = proportional_denton(raw, benchmarks)
    spatial = reconcile_spatial(
        denton,
        pd.read_csv(ROOT / "data/benchmarking/fies_2023_calabarzon_spatial_benchmark.csv"),
    )
    output_root.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_root / "raw_xgb_quarterly_indicators.csv", index=False)
    denton.to_csv(output_root / "denton_quarterly_estimates.csv", index=False)
    spatial.to_csv(output_root / "province_quarterly_estimates.csv", index=False)
    return {"raw": raw, "denton": denton, "spatial": spatial}


def run() -> None:
    """Run the pipeline when a valid Model B quarterly input exists.

    The current repository's regional quarterly LFS table intentionally fails at
    the inference boundary because it does not contain Model B's 129 features.
    """
    model = ModelBInference(
        ROOT / "models/xgboost_model_b_2018_2023.json",
        ROOT / "models/xgboost_model_features.json",
    )
    lfs = pd.read_csv(ROOT / "data/lfs/lfs_calabarzon_quarterly_features.csv")
    indicators = model.predict_from_quarterly_lfs(lfs)
    indicators.to_csv(ROOT / "outputs/raw_xgb_quarterly_indicators.csv", index=False)
    raise RuntimeError(
        "No annual benchmark was supplied. Provide explicit BenchmarkMetadata before "
        "running Denton; no current-year annual total is fabricated."
    )


if __name__ == "__main__":
    run()

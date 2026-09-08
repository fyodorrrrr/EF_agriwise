from pathlib import Path

import pandas as pd
import pytest

from pipeline.current_year import run_current_year_pipeline
from pipeline.denton import BenchmarkMetadata, DentonError, proportional_denton
from pipeline.inference import FeatureContractError, ModelBInference
from pipeline.indicator_projection import IncompleteYearError, IndicatorProjectionError
from pipeline.spatial import reconcile_spatial, validate_spatial_weights


ROOT = Path(__file__).resolve().parents[1]


def test_model_b_manifest_is_exactly_129_features_and_has_no_target():
    model = ModelBInference(
        ROOT / "models/xgboost_model_b_2018_2023.json",
        ROOT / "models/xgboost_model_features.json",
    )
    assert len(model.features) == 129
    assert "BREAD" not in model.features


def test_current_quarterly_lfs_cannot_be_fabricated_into_model_b_features():
    model = ModelBInference(
        ROOT / "models/xgboost_model_b_2018_2023.json",
        ROOT / "models/xgboost_model_features.json",
    )
    lfs = pd.read_csv(ROOT / "data/lfs/lfs_calabarzon_quarterly_features.csv")
    with pytest.raises(FeatureContractError, match="cannot be mapped to Model B"):
        model.predict_from_quarterly_lfs(lfs)


def test_proportional_denton_is_annually_additive():
    indicators = pd.DataFrame(
        {
            "year": [2023] * 4,
            "quarter": [1, 2, 3, 4],
            "raw_xgb_indicator": [10.0, 20.0, 15.0, 25.0],
        }
    )
    result = proportional_denton(
        indicators,
        {2023: BenchmarkMetadata(1000.0, 2023, "test observed", "observed")},
    )
    assert result["benchmarked_quarterly_demand"].sum() == pytest.approx(1000.0)


def test_denton_requires_an_explicit_benchmark():
    indicators = pd.DataFrame(
        {"year": [2026] * 4, "quarter": [1, 2, 3, 4], "raw_xgb_indicator": [1, 2, 3, 4]}
    )
    with pytest.raises(DentonError, match="annual benchmark mismatch"):
        proportional_denton(indicators, {})      

def test_spatial_weights_and_reconciliation_are_additive():
    weights = pd.DataFrame(
        {"PROVINCE": ["A", "B"], "SPATIAL_SHARE": [0.25, 0.75]}
    )
    validate_spatial_weights(weights, expected_provinces={"A", "B"})
    regional = pd.DataFrame(
        {"year": [2023], "quarter": [1], "benchmarked_quarterly_demand": [100.0]}
    )
    result = reconcile_spatial(regional, weights)
    assert result["province_quarterly_demand"].sum() == pytest.approx(100.0)


def test_spatial_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to one"):
        validate_spatial_weights(
            pd.DataFrame({"PROVINCE": ["A"], "SPATIAL_SHARE": [0.5]})
        )


def test_new_runtime_does_not_use_fixed_quarter_share_allocation():
    source = (ROOT / "pipeline/run_pipeline.py").read_text(encoding="utf-8")
    assert "QUARTER_SHARE_PERCENT" not in source


def _observed(quarters):
    return pd.DataFrame(
        {
            "year": [2026] * len(quarters),
            "quarter": quarters,
            "raw_xgb_indicator": [100.0 + quarter * 10 for quarter in quarters],
            "indicator_status": "model_derived",
            "indicator_source": "XGBoost",
            "as_of_date": "2026-09-30",
        }
    )


def _projection(quarters):
    return pd.DataFrame(
        {
            "year": [2026] * len(quarters),
            "quarter": quarters,
            "raw_xgb_indicator": [150.0 + quarter * 5 for quarter in quarters],
            "indicator_status": "forecast",
            "indicator_source": "test_projection",
            "as_of_date": "2026-09-30",
        }
    )


def _benchmark():
    return BenchmarkMetadata(1000.0, 2026, "test annual benchmark", "estimated")


def _weights():
    return pd.DataFrame(
        {"PROVINCE": ["A", "B"], "SPATIAL_SHARE": [0.25, 0.75]}
    )


def test_complete_current_year_still_runs_with_provenance():
    result = run_current_year_pipeline(
        _observed([1, 2, 3, 4]), _benchmark(), _weights(), current_quarter=4
    )
    assert set(result["raw"]["indicator_status"]) == {"model_derived"}
    assert result["denton"]["benchmarked_quarterly_demand"].sum() == pytest.approx(1000.0)


def test_q1_q3_observed_q4_forecast_runs_denton():
    result = run_current_year_pipeline(
        _observed([1, 2, 3]),
        _benchmark(),
        _weights(),
        current_quarter=3,
        projected_indicator_rows=_projection([4]),
    )
    assert result["raw"].loc[result["raw"]["quarter"] == 4, "indicator_status"].item() == "forecast"
    assert result["denton"]["benchmarked_quarterly_demand"].sum() == pytest.approx(1000.0)
    assert len(result["province"]) == 8


def test_q1_q2_observed_q3_q4_forecast_runs_denton():
    result = run_current_year_pipeline(
        _observed([1, 2]),
        _benchmark(),
        _weights(),
        current_quarter=2,
        projected_indicator_rows=_projection([3, 4]),
    )
    assert set(result["raw"].loc[result["raw"]["indicator_status"] == "forecast", "quarter"]) == {3, 4}


def test_q1_observed_q2_q4_forecast_runs_denton():
    result = run_current_year_pipeline(
        _observed([1]),
        _benchmark(),
        _weights(),
        current_quarter=1,
        projected_indicator_rows=_projection([2, 3, 4]),
    )
    assert len(result["denton"]) == 4


def test_incomplete_year_without_projections_fails_closed():
    with pytest.raises(IncompleteYearError, match="requires projected indicators"):
        run_current_year_pipeline(_observed([1, 2, 3]), _benchmark(), _weights(), current_quarter=3)


def test_projected_rows_cannot_overwrite_observed_quarters():
    with pytest.raises(IndicatorProjectionError, match="overwrite"):
        run_current_year_pipeline(
            _observed([1, 2, 3]),
            _benchmark(),
            _weights(),
            current_quarter=3,
            projected_indicator_rows=_projection([3, 4]),
        )


def test_duplicate_indicator_quarters_fail():
    duplicate = pd.concat([_observed([1, 2, 3]), _observed([3])], ignore_index=True)
    with pytest.raises(IndicatorProjectionError, match="duplicate"):
        run_current_year_pipeline(
            duplicate, _benchmark(), _weights(), current_quarter=3, projected_indicator_rows=_projection([4])
        )


def test_future_observed_quarter_is_forbidden_in_as_of_backtest():
    future_observed = _observed([1, 2, 3, 4])
    with pytest.raises(IndicatorProjectionError, match="future quarters"):
        run_current_year_pipeline(
            future_observed, _benchmark(), _weights(), current_quarter=2
        )


def test_carry_forward_is_explicit_development_baseline_only():
    result = run_current_year_pipeline(
        _observed([1, 2, 3]),
        _benchmark(),
        _weights(),
        current_quarter=3,
        projection_method="carry_forward_baseline",
        as_of_date="2026-09-30",
    )
    future = result["raw"].loc[result["raw"]["quarter"] == 4].iloc[0]
    assert future["indicator_status"] == "forecast"
    assert future["indicator_source"] == "carry_forward_baseline_development_only"

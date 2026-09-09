from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.forecast_service import ForecastService
from ml.synthetic.red_onion.build_red_onion_synthetic_pipeline import (
    PRICE,
    SUPPLY,
    SOURCE_DIR,
    build,
)

_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"
_PROVINCES = ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")


def test_builds_minimal_runtime_artifacts_and_model_free_bundles(tmp_path: Path):
    outputs = build(artifacts_dir=tmp_path)

    for spec in (SUPPLY, PRICE):
        frame = outputs[spec.name]
        assert list(frame.columns) == ["geolocation", "date", "target", spec.lag_column]
        assert set(frame["geolocation"]) == set(_PROVINCES)
        for _, group in frame.groupby("geolocation"):
            assert group["target"].notna().sum() == spec.observed_count
            future = group[group["target"].isna()]
            assert len(future) == spec.forecast_count
            assert future[spec.lag_column].notna().all()
            assert future["date"].min() > group.loc[group["target"].notna(), "date"].max()

        bundle = joblib.load(tmp_path / spec.name / "red_onion.joblib")
        assert bundle["verdict"] == "CAUTION"
        assert bundle["model"] is None
        assert bundle["strategy"] == "seasonal_naive"
        assert "Synthetic MVP" in bundle["limitations"][0]


def test_supply_and_price_lags_match_the_previous_year_source_value(tmp_path: Path):
    outputs = build(artifacts_dir=tmp_path)
    for spec in (SUPPLY, PRICE):
        source = pd.read_csv(SOURCE_DIR / spec.source_file, parse_dates=["date"])
        observed = source[source["status"] == "synthetic_historical"]
        frame = outputs[spec.name]
        future = frame[frame["target"].isna()]
        for row in future.itertuples(index=False):
            prior = observed[
                (observed["geolocation"] == row.geolocation)
                & (observed["date"] == row.date - pd.DateOffset(months=spec.lag_months))
            ].iloc[0]
            assert getattr(row, spec.lag_column) == prior[spec.value_column]


def test_live_red_onion_demand_is_unchanged_and_other_commodities_are_stable():
    before = ForecastService(ArtifactRegistry.load(_ARTIFACTS))
    demand_before = {province: before.outlook("Red Onion", province).demand for province in _PROVINCES}
    other_before = {
        (commodity, province): before.outlook(commodity, province)
        for commodity in ("Rice", "Tomato", "Banana")
        for province in _PROVINCES
    }

    build()

    after = ForecastService(ArtifactRegistry.load(_ARTIFACTS))
    for province in _PROVINCES:
        assert after.outlook("Red Onion", province).demand == demand_before[province]
    for key, before_outlook in other_before.items():
        assert after.outlook(*key) == before_outlook


def test_live_red_onion_uses_synthetic_components_and_existing_opportunity_scorer():
    service = ForecastService(ArtifactRegistry.load(_ARTIFACTS))
    outlook = service.outlook("Red Onion", "Laguna")

    assert len(outlook.supply.observed or []) == 8
    assert len(outlook.supply.forecast or []) == 4
    assert outlook.supply.unit == "MT"
    assert outlook.supply.source == "seasonal_naive"
    assert outlook.supply.confidence == "MODERATE"
    assert "Synthetic MVP" in outlook.supply.limitations[0]

    assert len(outlook.price.observed or []) == 12
    assert len(outlook.price.forecast or []) == 12
    assert outlook.price.unit == "PHP/kg"
    assert outlook.price.source == "seasonal_naive"
    assert outlook.price.confidence == "MODERATE"
    assert "Synthetic MVP" in outlook.price.limitations[0]

    assert outlook.opportunity.verdict == "PASS"
    assert outlook.opportunity.score is not None
    assert outlook.opportunity.classification is not None
    assert outlook.opportunity.shared_quarter == "2027-04-01"

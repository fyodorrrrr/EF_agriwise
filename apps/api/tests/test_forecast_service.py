from __future__ import annotations

from pathlib import Path

import joblib
import pytest

from ml.forecasting.artifact_registry import ArtifactRegistry, slugify_commodity
from ml.forecasting.forecast_service import ForecastService

_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"


def _service(tmp_path: Path) -> ForecastService:
    return ForecastService(ArtifactRegistry.load(tmp_path / "missing_artifacts"))


def _real_service() -> ForecastService:
    if not (_ARTIFACTS / "prepared").is_dir():
        pytest.skip("committed artifact bundle not present in this checkout")
    return ForecastService(ArtifactRegistry.load(_ARTIFACTS))


def test_catalog_is_independent_of_loaded_artifacts(tmp_path):
    payload = _service(tmp_path).catalog()

    assert payload.commodities == ("Rice", "Tomato", "Red Onion", "Banana")
    assert payload.provinces == ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")
    assert len(payload.pairs) == 20


def test_outlook_returns_insufficient_data_when_registry_is_empty(tmp_path):
    payload = _service(tmp_path).outlook("Tomato", "Cavite")

    assert payload.commodity == "Tomato"
    assert payload.province == "Cavite"
    assert payload.demand.verdict == "INSUFFICIENT_DATA"
    assert payload.supply.verdict == "INSUFFICIENT_DATA"
    assert payload.price.verdict == "INSUFFICIENT_DATA"
    assert payload.opportunity.verdict == "INSUFFICIENT_DATA"
    assert payload.opportunity.score is None
    assert payload.opportunity.classification is None


def test_outlook_reflects_a_loaded_artifacts_verdict_metrics_and_limitations(tmp_path):
    demand_dir = tmp_path / "demand"
    demand_dir.mkdir()
    joblib.dump(
        {
            "commodity": "Rice",
            "model_id": "rice-demand-v1",
            "verdict": "USABLE_PROXY",
            "metrics": {"r2": 0.548, "mae": 6159.0},
            "limitations": ["FIES expenditure-category proxy, not physical commodity demand."],
        },
        demand_dir / f"{slugify_commodity('Rice')}.joblib",
    )
    service = ForecastService(ArtifactRegistry.load(tmp_path))

    payload = service.outlook("Rice", "Laguna")

    assert payload.demand.verdict == "USABLE_PROXY"
    assert payload.demand.metrics == {"r2": 0.548, "mae": 6159.0}
    assert payload.demand.limitations == [
        "FIES expenditure-category proxy, not physical commodity demand."
    ]
    # No prepared demand-pressure table in this tmp bundle, so there is no
    # series to serve -- only the verdict/metrics/limitations from the joblib.
    assert payload.demand.observed is None
    assert payload.demand.forecast is None
    assert payload.demand.data_as_of is None
    # Components with no matching artifact still fall back cleanly.
    assert payload.supply.verdict == "INSUFFICIENT_DATA"
    assert payload.price.verdict == "INSUFFICIENT_DATA"


def test_outlook_reports_indicative_proxy_verdict_for_a_weak_demand_model(tmp_path):
    demand_dir = tmp_path / "demand"
    demand_dir.mkdir()
    joblib.dump(
        {
            "commodity": "Banana",
            "model_id": "banana-demand-v1",
            "verdict": "INDICATIVE_PROXY",
            "metrics": {"r2": 0.28, "mae": 2404.0},
            "limitations": ["FIES expenditure-category proxy, not physical commodity demand."],
        },
        demand_dir / f"{slugify_commodity('Banana')}.joblib",
    )
    service = ForecastService(ArtifactRegistry.load(tmp_path))

    payload = service.outlook("Banana", "Quezon")

    assert payload.demand.verdict == "INDICATIVE_PROXY"


# -- Sprint 2a value generation (against the committed artifact bundle) --


def test_demand_serves_the_committed_pressure_index_series():
    payload = _real_service().outlook("Rice", "Laguna")

    demand = payload.demand
    assert demand.verdict == "USABLE_PROXY"
    assert demand.unit == "index (base~100)"
    assert demand.frequency == "quarterly"
    assert demand.source == "demand_pressure_index"
    assert demand.label == "Cereal Household Demand Proxy"
    assert demand.observed and demand.forecast
    assert len(demand.forecast) == 3
    assert demand.data_as_of == "2025-10-01"
    assert demand.confidence == "MODERATE"


def test_supply_falls_back_to_seasonal_naive_without_a_model_joblib():
    supply = _real_service().outlook("Rice", "Laguna").supply

    # supply/rice.joblib is not in the committed bundle -> seasonal-naive.
    assert supply.verdict == "CAUTION"
    assert supply.unit == "MT"
    assert supply.source == "seasonal_naive"
    assert supply.forecast and all(p["value"] > 0 for p in supply.forecast)


def test_price_uses_the_learned_model_when_the_joblib_is_present():
    price = _real_service().outlook("Rice", "Laguna").price

    assert price.verdict == "PASS"
    assert price.unit == "PHP/kg"
    assert price.source.startswith("learned_model:")
    assert price.confidence == "HIGH"
    # Price is monthly; the committed feature table has 5 future months
    # prepared for Rice/Laguna, which is below the 12-month (4-quarter)
    # horizon cap — the cap only ever binds once more months are prepared.
    assert len(price.forecast) == 5


def test_red_onion_supply_and_price_stay_value_free():
    payload = _real_service().outlook("Red Onion", "Batangas")

    for component in (payload.supply, payload.price):
        assert component.verdict == "INSUFFICIENT_DATA"
        assert component.observed is None
        assert component.forecast is None
    # ...but its demand proxy series is available.
    assert payload.demand.forecast


def test_evidence_covers_all_twelve_components():
    evidence = _real_service().evidence()

    assert len(evidence) == 12
    by_key = {(e.commodity, e.component): e for e in evidence}

    rice_demand = by_key[("Rice", "demand")]
    assert rice_demand.target == "BREAD"
    assert rice_demand.model == "GradientBoostingRegressor"
    assert rice_demand.province_holdout  # per-province R2/MAE table

    rice_supply = by_key[("Rice", "supply")]
    assert rice_supply.target == "PSA volume of production"
    assert rice_supply.baseline.get("sMAPE")  # seasonal-naive baseline present

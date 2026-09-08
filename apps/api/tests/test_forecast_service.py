from __future__ import annotations

from pathlib import Path

import joblib

from ml.forecasting.artifact_registry import ArtifactRegistry, slugify_commodity
from ml.forecasting.forecast_service import ForecastService


def _service(tmp_path: Path) -> ForecastService:
    return ForecastService(ArtifactRegistry.load(tmp_path / "missing_artifacts"))


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
    # Forward-looking value/date generation is a separate, not-yet-designed
    # piece of work -- these stay unset even when an artifact is present.
    assert payload.demand.values is None
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

from __future__ import annotations

from pathlib import Path

from ml.forecasting.artifact_registry import ArtifactRegistry
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

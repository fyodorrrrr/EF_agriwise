from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routers.forecast import get_forecast_service
from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.forecast_service import ForecastService

client = TestClient(create_app())
_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"


def test_methodology_is_empty_but_valid_without_artifacts(tmp_path):
    app = create_app()
    app.dependency_overrides[get_forecast_service] = lambda: ForecastService(
        ArtifactRegistry.load(tmp_path / "nope")
    )
    body = TestClient(app).get("/forecast/methodology").json()

    assert body["demand"] == {} and body["opportunity"] == {}
    # disclaimers are always present — they are not artifact-derived
    assert any("peer-relative" in d for d in body["disclaimers"])


def test_methodology_assembles_from_the_committed_registry():
    if not (_ARTIFACTS / "reports" / "methodology_registry.json").is_file():
        pytest.skip("committed artifact bundle not present")

    body = client.get("/forecast/methodology").json()

    assert body["schema_version"] == "3.2"
    assert body["supply"]["frequency"] == "quarterly"
    assert body["price"]["frequency"] == "monthly"
    assert body["demand"]["targets"]["rice"] == "BREAD"
    assert body["opportunity"]["components"]["demand_pressure_index"]["weight"] == 0.35
    assert body["commodity_flow"]  # commodity_flow_methodology.json
    assert len(body["disclaimers"]) >= 3

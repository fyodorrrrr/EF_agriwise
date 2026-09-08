from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routers.forecast import get_forecast_service
from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.forecast_service import ForecastService

client = TestClient(create_app())


def test_catalog_lists_every_commodity_province_pair():
    response = client.get("/forecast/catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["commodities"] == ["Rice", "Tomato", "Red Onion", "Banana"]
    assert body["provinces"] == ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
    assert len(body["pairs"]) == 20
    assert {"commodity": "Rice", "province": "Laguna"} in body["pairs"]


def test_outlook_reports_insufficient_data_for_every_component_without_artifacts(tmp_path):
    # Isolated from whatever is actually on disk under ml/artifacts/ (which is
    # populated once real models are trained and promoted) via a dependency
    # override, so this stays a true "empty registry" scenario regardless of
    # repo state.
    app = create_app()
    app.dependency_overrides[get_forecast_service] = lambda: ForecastService(
        ArtifactRegistry.load(tmp_path / "missing_artifacts")
    )
    isolated_client = TestClient(app)

    response = isolated_client.get(
        "/forecast/outlook", params={"commodity": "Rice", "province": "Laguna"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["commodity"] == "Rice"
    assert body["province"] == "Laguna"
    assert "province-resolution" in body["resolution_note"]
    for component in ("demand", "supply", "price"):
        assert body[component]["verdict"] == "INSUFFICIENT_DATA"
        assert body[component]["observed"] is None
        assert body[component]["forecast"] is None
    assert body["opportunity"]["verdict"] == "INSUFFICIENT_DATA"
    assert body["opportunity"]["score"] is None


def test_outlook_reflects_real_artifacts_when_ml_artifacts_is_populated():
    # Exercises the real ml/artifacts/ directory wired up via settings (as
    # populated by running trainings_file/AgriWise_Complete_Modeling_V3_2.ipynb
    # and its EF_agriwise artifact-promotion cell). Skips cleanly in a fresh
    # checkout where nothing has been trained yet.
    response = client.get("/forecast/outlook", params={"commodity": "Rice", "province": "Laguna"})
    body = response.json()
    if body["demand"]["verdict"] == "INSUFFICIENT_DATA" and not body["demand"]["metrics"]:
        pytest.skip("ml/artifacts/ is not populated in this checkout")

    assert body["demand"]["verdict"] in {"USABLE_PROXY", "INDICATIVE_PROXY", "CAUTION", "PASS"}
    assert isinstance(body["demand"]["metrics"], dict) and body["demand"]["metrics"]
    assert body["demand"]["limitations"]


def test_outlook_rejects_unknown_commodity():
    response = client.get("/forecast/outlook", params={"commodity": "Mango", "province": "Laguna"})

    assert response.status_code == 422


def test_evidence_returns_a_component_per_commodity_and_kind():
    response = client.get("/forecast/evidence")

    assert response.status_code == 200
    components = response.json()["components"]
    assert len(components) == 12
    keys = {(c["commodity"], c["component"]) for c in components}
    assert ("Rice", "demand") in keys and ("Banana", "price") in keys
    for c in components:
        assert c["verdict"] in {
            "PASS",
            "CAUTION",
            "INSUFFICIENT_DATA",
            "USABLE_PROXY",
            "INDICATIVE_PROXY",
        }
        assert c["province_resolution"] == "province"

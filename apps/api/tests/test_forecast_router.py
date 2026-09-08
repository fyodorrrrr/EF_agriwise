from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_catalog_lists_every_commodity_province_pair():
    response = client.get("/forecast/catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["commodities"] == ["Rice", "Tomato", "Red Onion", "Banana"]
    assert body["provinces"] == ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
    assert len(body["pairs"]) == 20
    assert {"commodity": "Rice", "province": "Laguna"} in body["pairs"]


def test_outlook_reports_insufficient_data_for_every_component_without_artifacts():
    response = client.get("/forecast/outlook", params={"commodity": "Rice", "province": "Laguna"})

    assert response.status_code == 200
    body = response.json()
    assert body["commodity"] == "Rice"
    assert body["province"] == "Laguna"
    assert "province-resolution" in body["resolution_note"]
    for component in ("demand", "supply", "price"):
        assert body[component]["verdict"] == "INSUFFICIENT_DATA"
        assert body[component]["values"] is None
    assert body["opportunity"]["verdict"] == "INSUFFICIENT_DATA"
    assert body["opportunity"]["score"] is None


def test_outlook_rejects_unknown_commodity():
    response = client.get("/forecast/outlook", params={"commodity": "Mango", "province": "Laguna"})

    assert response.status_code == 422

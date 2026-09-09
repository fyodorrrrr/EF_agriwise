from fastapi.testclient import TestClient

from app.main import create_app


def test_advisory_returns_safe_frontend_payload():
    with TestClient(create_app()) as client:
        response = client.get("/advisory", params={"province": "Laguna"})

    assert response.status_code == 200
    body = response.json()
    assert body["province"] == "Laguna"
    assert len(body["advisories"]) == 4
    assert all("municipalities" not in item for item in body["advisories"])
    red_onion = next(item for item in body["advisories"] if item["commodity"] == "Red Onion")
    assert red_onion["signals"]["physical_gap"] is not None
    assert red_onion["supply"]["limitations"] == [
        "Synthetic MVP supply data for proof-of-functioning concept."
    ]
    rice = next(item for item in body["advisories"] if item["commodity"] == "Rice")
    assert rice["signals"]["physical_gap"] is None

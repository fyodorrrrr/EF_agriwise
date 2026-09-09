from __future__ import annotations

from types import SimpleNamespace

import pytest

from ml.forecasting.municipal_disaggregation import MunicipalDisaggregationService


class StubForecastService:
    def outlook(self, commodity: str, province: str):
        assert commodity == "Tomato"
        assert province in {"Laguna", "Cavite"}
        return SimpleNamespace(
            supply=SimpleNamespace(verdict="CAUTION", forecast=[{"value": 797.77}], observed=None)
        )


def test_laguna_benchmark_joins_thirty_rows_and_preserves_supply_additivity():
    payload = MunicipalDisaggregationService(StubForecastService()).outlook("Tomato", "Laguna")

    assert len(payload.municipalities) == 30
    assert len({item["psgc_code"] for item in payload.municipalities}) == 30
    assert sum(item["demand_value"] for item in payload.municipalities) == pytest.approx(100)
    assert sum(item["supply_mt"] for item in payload.municipalities) == pytest.approx(797.77)
    assert all(item["opportunity_score"] is not None for item in payload.municipalities)
    assert all(item["opportunity_classification"] for item in payload.municipalities)


def test_non_laguna_has_no_synthetic_municipal_records():
    payload = MunicipalDisaggregationService(StubForecastService()).outlook("Tomato", "Cavite")

    assert payload.municipalities == ()

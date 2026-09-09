from __future__ import annotations

from types import SimpleNamespace

import pytest

from ml.forecasting.municipal_disaggregation import (
    MunicipalDisaggregationService,
    load_municipal_benchmark,
)


EXPECTED_LGU_COUNTS = {
    "Batangas": 34,
    "Cavite": 23,
    "Laguna": 30,
    "Quezon": 40,
    "Rizal": 14,
}


class StubForecastService:
    def outlook(self, commodity: str, province: str):
        assert commodity == "Tomato"
        assert province in EXPECTED_LGU_COUNTS
        return SimpleNamespace(
            supply=SimpleNamespace(verdict="CAUTION", forecast=[{"value": 797.77}], observed=None)
        )


@pytest.mark.parametrize(("province", "expected_count"), EXPECTED_LGU_COUNTS.items())
def test_benchmark_joins_expected_rows_and_preserves_supply_additivity(
    province: str, expected_count: int
):
    payload = MunicipalDisaggregationService(StubForecastService()).outlook("Tomato", province)

    assert len(payload.municipalities) == expected_count
    assert len({item["psgc_code"] for item in payload.municipalities}) == expected_count
    assert sum(item["demand_value"] for item in payload.municipalities) == pytest.approx(100)
    assert sum(item["supply_mt"] for item in payload.municipalities) == pytest.approx(797.77)
    assert all(item["opportunity_score"] is not None for item in payload.municipalities)
    assert all(item["opportunity_classification"] for item in payload.municipalities)


@pytest.mark.parametrize("province", EXPECTED_LGU_COUNTS)
def test_benchmark_weights_sum_to_one_per_commodity(province: str):
    benchmark = load_municipal_benchmark(province)

    for records in benchmark.values():
        assert sum(record.demand_weight for record in records) == pytest.approx(1)
        assert sum(record.supply_weight for record in records) == pytest.approx(1)

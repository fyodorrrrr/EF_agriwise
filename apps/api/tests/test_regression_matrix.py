"""Sprint 6, Task 6.1 — full commodity x province analytical regression.

Runs the real committed artifact bundle through `/forecast/outlook` for every
one of the 20 combinations and asserts the matrix from Section 1 of the plan.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.domain import COMMODITIES, PROVINCES
from ml.forecasting.forecast_service import ForecastService

_ARTIFACTS = Path(__file__).resolve().parents[3] / "ml" / "artifacts"
_PROXY_VERDICTS = {"USABLE_PROXY", "INDICATIVE_PROXY"}


@pytest.fixture(scope="module")
def service() -> ForecastService:
    if not (_ARTIFACTS / "prepared").is_dir():
        pytest.skip("committed artifact bundle not present")
    return ForecastService(ArtifactRegistry.load(_ARTIFACTS))


@pytest.mark.parametrize("commodity", COMMODITIES)
@pytest.mark.parametrize("province", PROVINCES)
def test_every_combination(service: ForecastService, commodity: str, province: str):
    outlook = service.outlook(commodity, province)
    assert outlook.commodity == commodity and outlook.province == province
    assert "province-resolution" in outlook.resolution_note

    # -- demand: always an Estimated Demand Proxy index, every commodity --
    demand = outlook.demand
    assert demand.verdict in _PROXY_VERDICTS
    assert demand.unit is None or "index" in demand.unit
    assert demand.frequency == "quarterly"
    assert demand.forecast, "every commodity has a 3-quarter demand proxy forecast"

    # -- supply: MT quarterly, or value-free INSUFFICIENT_DATA --
    supply = outlook.supply
    if commodity == "Red Onion":
        assert supply.verdict == "INSUFFICIENT_DATA"
        assert supply.observed is None and supply.forecast is None
    else:
        assert supply.verdict in {"PASS", "CAUTION"}
        assert supply.unit == "MT" and supply.frequency == "quarterly"
        assert supply.forecast and supply.source in {
            "seasonal_naive",
            *(f"learned_model:{s}" for s in ("hist_gradient_boosting", "random_forest")),
        }

    # -- price: PHP/kg monthly, or value-free --
    price = outlook.price
    if commodity == "Red Onion":
        assert price.verdict == "INSUFFICIENT_DATA"
        assert price.observed is None and price.forecast is None
    else:
        assert price.verdict in {"PASS", "CAUTION"}
        assert price.unit == "PHP/kg" and price.frequency == "monthly"
        assert price.forecast

    # -- opportunity --
    opp = outlook.opportunity
    if commodity == "Red Onion":
        assert opp.verdict == "INSUFFICIENT_DATA" and opp.score is None
    else:
        assert opp.verdict == "PASS"
        assert 0.0 <= opp.score <= 100.0
        assert opp.shared_quarter and opp.shared_quarter.endswith(("-01-01", "-04-01", "-07-01", "-10-01"))
        # weights renormalize to 1 and market_flow (no data) is excluded
        assert "market_flow_dependence_index" not in opp.weights_used
        assert abs(sum(opp.weights_used.values()) - 1.0) < 1e-6


def test_repeated_full_sweep_is_deterministic(service: ForecastService):
    def snapshot():
        return {
            (c, p): service.outlook(c, p).opportunity.score
            for c in COMMODITIES
            for p in PROVINCES
        }

    assert snapshot() == snapshot()

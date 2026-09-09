"""Laguna's synthetic municipal benchmark disaggregated from province outlooks."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ml.forecasting.forecast_service import ForecastService

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BENCHMARK_PATH = _REPO_ROOT / "data" / "synthetic_data" / "laguna_municipal_benchmark_v1.csv"


@dataclass(frozen=True)
class MunicipalBenchmark:
    psgc_code: str
    municipality: str
    demand_weight: float
    supply_weight: float
    opportunity_score: float
    opportunity_classification: str


@dataclass(frozen=True)
class MunicipalOutlookPayload:
    province: str
    commodity: str
    methodology: str
    demand_unit: str
    supply_unit: str
    municipalities: tuple[dict, ...]


@lru_cache
def load_laguna_benchmark(
    path: Path = _BENCHMARK_PATH,
) -> dict[str, tuple[MunicipalBenchmark, ...]]:
    """Load the committed CSV once, keyed by commodity and then PSGC downstream."""
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = csv.DictReader(source)
        required = {
            "commodity",
            "psgc_code",
            "municipality",
            "demand_weight",
            "supply_weight",
            "municipal_opportunity_score_v1",
            "municipal_opportunity_classification_v1",
        }
        if not rows.fieldnames or not required.issubset(rows.fieldnames):
            raise ValueError(f"municipal benchmark has an unsupported schema: {path}")

        grouped: dict[str, list[MunicipalBenchmark]] = {}
        for row in rows:
            benchmark = MunicipalBenchmark(
                psgc_code=row["psgc_code"],
                municipality=row["municipality"],
                demand_weight=float(row["demand_weight"]),
                supply_weight=float(row["supply_weight"]),
                opportunity_score=float(row["municipal_opportunity_score_v1"]),
                opportunity_classification=row["municipal_opportunity_classification_v1"],
            )
            grouped.setdefault(row["commodity"], []).append(benchmark)
    return {commodity: tuple(records) for commodity, records in grouped.items()}


def _latest_value(component) -> float | None:
    if component.verdict == "INSUFFICIENT_DATA":
        return None
    points = component.forecast or component.observed or []
    if not points:
        return None
    value = points[-1]["value"] if isinstance(points[-1], dict) else points[-1].value
    return float(value)


class MunicipalDisaggregationService:
    """Exposes the CSV benchmark beneath the existing province-level forecast."""

    def __init__(self, forecast_service: ForecastService, benchmark_path: Path = _BENCHMARK_PATH):
        self._forecast_service = forecast_service
        self._benchmark_path = benchmark_path

    def outlook(self, commodity: str, province: str) -> MunicipalOutlookPayload:
        # The MVP deliberately publishes data only for Laguna; other provinces
        # receive an empty collection rather than fabricated municipal values.
        records = (
            load_laguna_benchmark(self._benchmark_path).get(commodity, ())
            if province == "Laguna"
            else ()
        )
        provincial = self._forecast_service.outlook(commodity, province)
        supply_mt = _latest_value(provincial.supply)

        municipalities = tuple(
            {
                "psgc_code": record.psgc_code,
                "municipality": record.municipality,
                "demand_weight": record.demand_weight,
                # Demand is an index in the deployed forecast, not an additive MT
                # control. The benchmark share is intentionally returned as percent.
                "demand_value": record.demand_weight * 100,
                "demand_unit": "Synthetic Demand Share (%)",
                "supply_weight": record.supply_weight,
                "supply_mt": supply_mt * record.supply_weight if supply_mt is not None else None,
                "opportunity_score": record.opportunity_score,
                "opportunity_classification": record.opportunity_classification,
            }
            for record in records
        )
        return MunicipalOutlookPayload(
            province=province,
            commodity=commodity,
            methodology="synthetic_municipal_benchmark_v1",
            demand_unit="Synthetic Demand Share (%)",
            supply_unit="MT",
            municipalities=municipalities,
        )

"""Synthetic municipal benchmark disaggregation beneath province outlooks."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ml.forecasting.forecast_service import ForecastService

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BENCHMARK_DIR = _PROJECT_ROOT / "data" / "synthetic_data"
SUPPORTED_MUNICIPAL_BENCHMARKS = {
    "Batangas": "batangas_municipal_benchmark_v1.csv",
    "Cavite": "cavite_municipal_benchmark_v1.csv",
    "Laguna": "laguna_municipal_benchmark_v1.csv",
    "Quezon": "quezon_municipal_benchmark_v1.csv",
    "Rizal": "rizal_municipal_benchmark_v1.csv",
}
_CANONICAL_PROVINCES = {province.casefold(): province for province in SUPPORTED_MUNICIPAL_BENCHMARKS}


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


def _canonical_province(province: str) -> str:
    canonical = _CANONICAL_PROVINCES.get(province.strip().casefold())
    if canonical is None:
        raise ValueError(f"municipal benchmark is not supported for province {province!r}")
    return canonical


@lru_cache
def load_municipal_benchmark(
    province: str,
    benchmark_dir: Path = _BENCHMARK_DIR,
) -> dict[str, tuple[MunicipalBenchmark, ...]]:
    """Load one allow-listed province CSV once, keyed by commodity."""
    canonical_province = _canonical_province(province)
    path = benchmark_dir / SUPPORTED_MUNICIPAL_BENCHMARKS[canonical_province]
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

    result = {commodity: tuple(records) for commodity, records in grouped.items()}
    for commodity, records in result.items():
        if len({record.psgc_code for record in records}) != len(records):
            raise ValueError(f"municipal benchmark has duplicate PSGC codes: {path} ({commodity})")
        for field_name in ("demand_weight", "supply_weight"):
            values = [getattr(record, field_name) for record in records]
            if not all(math.isfinite(value) and value >= 0 for value in values):
                raise ValueError(f"municipal benchmark has invalid {field_name}: {path} ({commodity})")
            if not math.isclose(sum(values), 1.0, rel_tol=0, abs_tol=1e-8):
                raise ValueError(f"municipal benchmark {field_name} must sum to one: {path} ({commodity})")
    return result


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

    def __init__(self, forecast_service: ForecastService, benchmark_dir: Path = _BENCHMARK_DIR):
        self._forecast_service = forecast_service
        self._benchmark_dir = benchmark_dir

    def outlook(self, commodity: str, province: str) -> MunicipalOutlookPayload:
        canonical_province = _canonical_province(province)
        records = load_municipal_benchmark(canonical_province, self._benchmark_dir).get(commodity, ())
        provincial = self._forecast_service.outlook(commodity, canonical_province)
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
            province=canonical_province,
            commodity=commodity,
            methodology="synthetic_municipal_benchmark_v1",
            demand_unit="Synthetic Demand Share (%)",
            supply_unit="MT",
            municipalities=municipalities,
        )

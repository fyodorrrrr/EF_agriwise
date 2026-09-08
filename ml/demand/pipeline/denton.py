"""Proportional Denton temporal benchmarking.

The implementation solves for z_t = Y_t / p_t and minimizes first differences
of z_t subject to annual additive constraints. It does not modify predictors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd


class DentonError(ValueError):
    """Raised when proportional Denton inputs are not defensible."""


@dataclass(frozen=True)
class BenchmarkMetadata:
    """Explicit provenance for one annual benchmark."""

    benchmark_value: float
    benchmark_year: int
    benchmark_source: str
    benchmark_status: str

    def __post_init__(self) -> None:
        if not np.isfinite(self.benchmark_value) or self.benchmark_value < 0:
            raise DentonError("benchmark_value must be finite and non-negative")
        if self.benchmark_status not in {"observed", "estimated", "forecast", "provisional"}:
            raise DentonError(f"unsupported benchmark_status: {self.benchmark_status}")
        if not self.benchmark_source.strip():
            raise DentonError("benchmark_source is required")


def proportional_denton(
    indicators: pd.DataFrame,
    benchmarks: Mapping[int, BenchmarkMetadata],
    *,
    indicator_column: str = "raw_xgb_indicator",
    year_column: str = "year",
    quarter_column: str = "quarter",
    tolerance: float = 1e-7,
) -> pd.DataFrame:
    """Benchmark positive quarterly indicators to explicit annual totals.

    The optimization is expressed in ratio space. If z_t = Y_t / p_t, this
    minimizes sum((z_t - z_(t-1)) ** 2) subject to annual sums of Y_t.
    Missing quarters, non-positive indicators, incomplete years, and missing
    annual benchmarks fail closed because proportional Denton is undefined or
    ambiguous in those cases.
    """
    required = {year_column, quarter_column, indicator_column}
    missing = sorted(required.difference(indicators.columns))
    if missing:
        raise DentonError(f"indicator table is missing columns: {', '.join(missing)}")
    provenance_columns = [
        column
        for column in ("indicator_status", "indicator_source", "as_of_date")
        if column in indicators.columns
    ]
    frame = indicators[
        [year_column, quarter_column, indicator_column, *provenance_columns]
    ].copy()
    frame = frame.rename(
        columns={
            year_column: "year",
            quarter_column: "quarter",
            indicator_column: "raw_xgb_indicator",
        }
    )
    frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype(int)
    frame["quarter"] = pd.to_numeric(frame["quarter"], errors="raise").astype(int)
    frame["raw_xgb_indicator"] = pd.to_numeric(frame["raw_xgb_indicator"], errors="raise")
    if frame.duplicated(["year", "quarter"]).any():
        raise DentonError("indicator table contains duplicate year/quarter rows")
    if not np.isfinite(frame["raw_xgb_indicator"]).all():
        raise DentonError("indicator table contains NaN or infinite indicators")
    if (frame["raw_xgb_indicator"] <= tolerance).any():
        raise DentonError("proportional Denton requires indicators greater than tolerance")
    if not frame["quarter"].isin([1, 2, 3, 4]).all():
        raise DentonError("quarter must be one of 1, 2, 3, or 4")
    frame = frame.sort_values(["year", "quarter"]).reset_index(drop=True)

    years = sorted(frame["year"].unique().tolist())
    if set(benchmarks) != set(years):
        missing_years = sorted(set(years).difference(benchmarks))
        extra_years = sorted(set(benchmarks).difference(years))
        raise DentonError(f"annual benchmark mismatch; missing={missing_years}, extra={extra_years}")
    for year, group in frame.groupby("year", sort=False):
        if len(group) != 4 or set(group["quarter"]) != {1, 2, 3, 4}:
            raise DentonError(f"year {year} does not contain exactly four quarters")
        metadata = benchmarks[int(year)]
        if metadata.benchmark_year != int(year):
            raise DentonError(f"benchmark metadata year mismatch for {year}")

    p = frame["raw_xgb_indicator"].to_numpy(dtype=float)
    n = len(frame)
    difference = np.zeros((n - 1, n), dtype=float)
    for row in range(n - 1):
        difference[row, row] = -1.0
        difference[row, row + 1] = 1.0
    hessian = difference.T @ difference

    constraint = np.zeros((len(years), n), dtype=float)
    rhs = np.zeros(len(years), dtype=float)
    for row, year in enumerate(years):
        indexes = frame.index[frame["year"] == year].to_numpy()
        constraint[row, indexes] = p[indexes]
        rhs[row] = benchmarks[year].benchmark_value

    kkt = np.block([[hessian, constraint.T], [constraint, np.zeros((len(years), len(years)))]])
    solution = np.linalg.lstsq(kkt, np.concatenate([np.zeros(n), rhs]), rcond=None)[0][:n]
    estimates = p * solution
    if not np.isfinite(estimates).all() or (estimates < -tolerance).any():
        raise DentonError("Denton produced invalid quarterly estimates")
    estimates = np.maximum(estimates, 0.0)
    frame["benchmarked_quarterly_demand"] = estimates
    frame["annual_benchmark"] = frame["year"].map(
        {year: benchmarks[year].benchmark_value for year in years}
    )
    frame["benchmark_source"] = frame["year"].map(
        {year: benchmarks[year].benchmark_source for year in years}
    )
    frame["benchmark_status"] = frame["year"].map(
        {year: benchmarks[year].benchmark_status for year in years}
    )
    for year, group in frame.groupby("year"):
        if abs(group["benchmarked_quarterly_demand"].sum() - benchmarks[int(year)].benchmark_value) > tolerance:
            raise DentonError(f"Denton annual additivity failed for {year}")
    return frame

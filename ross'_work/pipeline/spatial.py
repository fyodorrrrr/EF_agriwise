"""Spatial reconciliation using fixed base-year FIES shares."""

from __future__ import annotations

import numpy as np
import pandas as pd


class SpatialError(ValueError):
    """Raised when spatial base-year shares are invalid."""


def validate_spatial_weights(
    weights: pd.DataFrame,
    *,
    province_column: str = "PROVINCE",
    share_column: str = "SPATIAL_SHARE",
    expected_provinces: set[str] | None = None,
    tolerance: float = 1e-7,
) -> pd.DataFrame:
    required = {province_column, share_column}
    missing = sorted(required.difference(weights.columns))
    if missing:
        raise SpatialError(f"spatial benchmark is missing columns: {', '.join(missing)}")
    result = weights[[province_column, share_column]].copy()
    result.columns = ["province", "spatial_share"]
    if result["province"].duplicated().any():
        raise SpatialError("spatial benchmark contains duplicate provinces")
    result["spatial_share"] = pd.to_numeric(result["spatial_share"], errors="raise")
    if not np.isfinite(result["spatial_share"]).all() or (result["spatial_share"] < 0).any():
        raise SpatialError("spatial shares must be finite and non-negative")
    if abs(float(result["spatial_share"].sum()) - 1.0) > tolerance:
        raise SpatialError("spatial shares must sum to one")
    if expected_provinces is not None and set(result["province"]) != expected_provinces:
        raise SpatialError("spatial benchmark provinces do not match expected provinces")
    return result


def reconcile_spatial(
    regional: pd.DataFrame,
    weights: pd.DataFrame,
    *,
    regional_column: str = "benchmarked_quarterly_demand",
    tolerance: float = 1e-7,
) -> pd.DataFrame:
    """Allocate each regional quarterly estimate with fixed base-year shares."""
    required = {"year", "quarter", regional_column}
    missing = sorted(required.difference(regional.columns))
    if missing:
        raise SpatialError(f"regional estimates are missing columns: {', '.join(missing)}")
    base = validate_spatial_weights(weights)
    rows = regional[["year", "quarter", regional_column]].copy()
    rows[regional_column] = pd.to_numeric(rows[regional_column], errors="raise")
    if not np.isfinite(rows[regional_column]).all() or (rows[regional_column] < 0).any():
        raise SpatialError("regional estimates must be finite and non-negative")
    rows["_key"] = 1
    base["_key"] = 1
    result = rows.merge(base, on="_key", how="outer").drop(columns="_key")
    result["province_quarterly_demand"] = (
        result[regional_column] * result["spatial_share"]
    )
    for (year, quarter), group in result.groupby(["year", "quarter"]):
        regional_value = float(group[regional_column].iloc[0])
        if abs(group["province_quarterly_demand"].sum() - regional_value) > tolerance:
            raise SpatialError(f"spatial reconciliation failed for {year}-Q{quarter}")
    result["spatial_weight_base_year"] = "2023 FIES"
    return result.rename(columns={regional_column: "regional_quarterly_demand"})[
        [
            "year",
            "quarter",
            "province",
            "regional_quarterly_demand",
            "spatial_share",
            "province_quarterly_demand",
            "spatial_weight_base_year",
        ]
    ]

"""Future quarterly indicator completion before annual Denton benchmarking."""

from __future__ import annotations

from datetime import date
from typing import Literal

import numpy as np
import pandas as pd


INDICATOR_STATUSES = {"observed", "model_derived", "forecast", "provisional"}
ProjectionMethod = Literal["explicit", "carry_forward_baseline"]


class IncompleteYearError(ValueError):
    """Raised when annual Denton lacks a complete indicator vector."""


class IndicatorProjectionError(ValueError):
    """Raised when indicator provenance or as-of rules are invalid."""


def _validate_indicator_rows(rows: pd.DataFrame, *, name: str) -> pd.DataFrame:
    required = {
        "year",
        "quarter",
        "raw_xgb_indicator",
        "indicator_status",
        "indicator_source",
        "as_of_date",
    }
    missing = sorted(required.difference(rows.columns))
    if missing:
        raise IndicatorProjectionError(f"{name} is missing columns: {', '.join(missing)}")
    result = rows[list(required)].copy()
    result["year"] = pd.to_numeric(result["year"], errors="raise").astype(int)
    result["quarter"] = pd.to_numeric(result["quarter"], errors="raise").astype(int)
    result["raw_xgb_indicator"] = pd.to_numeric(
        result["raw_xgb_indicator"], errors="raise"
    )
    if not np.isfinite(result["raw_xgb_indicator"]).all() or (
        result["raw_xgb_indicator"] <= 0
    ).any():
        raise IndicatorProjectionError(
            f"{name} indicators must be finite and strictly positive"
        )
    if not result["quarter"].isin([1, 2, 3, 4]).all():
        raise IndicatorProjectionError(f"{name} quarters must be 1, 2, 3, or 4")
    if not result["indicator_status"].isin(INDICATOR_STATUSES).all():
        raise IndicatorProjectionError(f"{name} contains an unsupported indicator_status")
    if result["indicator_source"].isna().any() or (
        result["indicator_source"].astype(str).str.strip() == ""
    ).any():
        raise IndicatorProjectionError(f"{name} requires indicator_source provenance")
    parsed_dates = pd.to_datetime(result["as_of_date"], errors="coerce")
    if parsed_dates.isna().any():
        raise IndicatorProjectionError(f"{name} contains invalid as_of_date values")
    result["as_of_date"] = parsed_dates.dt.strftime("%Y-%m-%d")
    if result.duplicated(["year", "quarter"]).any():
        raise IndicatorProjectionError(f"{name} contains duplicate year/quarter rows")
    return result.sort_values(["year", "quarter"]).reset_index(drop=True)


def project_missing_quarters(
    indicator_history: pd.DataFrame,
    target_year: int,
    current_quarter: int,
    *,
    projected_indicator_rows: pd.DataFrame | None = None,
    method: ProjectionMethod = "explicit",
    as_of_date: str | date | None = None,
) -> pd.DataFrame:
    """Return a complete target-year indicator vector with provenance.

    The default ``explicit`` method requires callers to supply future-quarter
    forecast indicators. ``carry_forward_baseline`` is only a development
    baseline and is never selected implicitly.
    """
    if target_year < 1 or current_quarter not in {1, 2, 3, 4}:
        raise IndicatorProjectionError("target_year/current_quarter is invalid")
    if method not in {"explicit", "carry_forward_baseline"}:
        raise IndicatorProjectionError(f"unsupported projection method: {method}")
    observed = _validate_indicator_rows(indicator_history, name="indicator_history")
    if (observed["year"] == target_year).sum() == 0:
        raise IncompleteYearError(f"no indicators supplied for target year {target_year}")
    target_rows = observed.loc[observed["year"] == target_year].copy()
    future_observed = target_rows.loc[target_rows["quarter"] > current_quarter]
    if not future_observed.empty and future_observed["indicator_status"].isin(
        {"observed", "model_derived", "provisional"}
    ).any():
        raise IndicatorProjectionError(
            "future quarters cannot be marked observed/model_derived/provisional "
            "relative to the forecast quarter"
        )
    if target_rows.loc[target_rows["quarter"] <= current_quarter, "indicator_status"].eq(
        "forecast"
    ).any():
        raise IndicatorProjectionError("past or current quarters cannot be forecast indicators")

    missing_quarters = sorted(set(range(1, 5)).difference(target_rows["quarter"]))
    future_missing = [quarter for quarter in missing_quarters if quarter > current_quarter]
    past_missing = [quarter for quarter in missing_quarters if quarter <= current_quarter]
    if past_missing:
        raise IncompleteYearError(
            f"target year {target_year} is missing quarter(s) that have already occurred: "
            f"{past_missing}"
        )
    if not future_missing:
        complete = target_rows
    else:
        if method == "explicit":
            if projected_indicator_rows is None:
                raise IncompleteYearError(
                    f"Annual Denton for {target_year} requires projected indicators for "
                    f"Q{future_missing[0]}-Q4 before the annual benchmark can be imposed."
                )
            projections = _validate_indicator_rows(
                projected_indicator_rows, name="projected_indicator_rows"
            )
            projections = projections.loc[projections["year"] == target_year].copy()
            if target_rows["quarter"].isin(projections["quarter"]).any():
                raise IndicatorProjectionError(
                    "projected indicators cannot overwrite observed/model-derived quarters"
                )
            if set(projections["quarter"]) != set(future_missing):
                raise IncompleteYearError(
                    f"explicit projections must contain exactly future missing quarters "
                    f"{future_missing}"
                )
            if (projections["quarter"] <= current_quarter).any():
                raise IndicatorProjectionError(
                    "projected indicators must be later than current_quarter"
                )
            if not projections["indicator_status"].eq("forecast").all():
                raise IndicatorProjectionError(
                    "future projected rows must have indicator_status='forecast'"
                )
            complete = pd.concat([target_rows, projections], ignore_index=True)
        else:
            if as_of_date is None:
                raise IndicatorProjectionError(
                    "as_of_date is required for carry-forward baseline projections"
                )
            last = target_rows.loc[target_rows["quarter"] <= current_quarter]
            if last.empty:
                raise IncompleteYearError("carry-forward baseline has no current-year source indicator")
            value = float(last.sort_values("quarter")["raw_xgb_indicator"].iloc[-1])
            forecast_date = pd.Timestamp(as_of_date).strftime("%Y-%m-%d")
            generated = pd.DataFrame(
                {
                    "year": target_year,
                    "quarter": future_missing,
                    "raw_xgb_indicator": value,
                    "indicator_status": "forecast",
                    "indicator_source": "carry_forward_baseline_development_only",
                    "as_of_date": forecast_date,
                }
            )
            complete = pd.concat([target_rows, generated], ignore_index=True)

    complete = _validate_indicator_rows(complete, name="completed_indicator_series")
    if set(complete["quarter"]) != {1, 2, 3, 4}:
        raise IncompleteYearError(f"target year {target_year} does not have Q1-Q4 indicators")
    if (complete["quarter"] <= current_quarter).any():
        invalid = complete.loc[
            complete["quarter"] <= current_quarter, "indicator_status"
        ].isin({"forecast"})
        if invalid.any():
            raise IndicatorProjectionError(
                "completed series contains a forecast indicator at or before current_quarter"
            )
    return complete.sort_values("quarter").reset_index(drop=True)

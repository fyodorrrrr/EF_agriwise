"""Prepare synthetic Red Onion supply and price runtime artifacts.

This pipeline transforms only ``data/synthetic_data/red_onion`` inputs.  It
does not read or modify the PSA/Denton Red Onion demand pipeline or artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from ml.forecasting.domain import PROVINCES

ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "data" / "synthetic_data" / "red_onion"
ARTIFACTS_DIR = ROOT / "ml" / "artifacts"

_COMMODITY = "Red Onion"
_HISTORICAL = "synthetic_historical"
_FORECAST = "synthetic_forecast"


@dataclass(frozen=True)
class ComponentSpec:
    name: str
    source_file: str
    value_column: str
    period: str
    lag_column: str
    lag_periods: int
    lag_months: int
    observed_count: int
    forecast_count: int
    unit: str


SUPPLY = ComponentSpec(
    name="supply",
    source_file="red_onion_supply_source.csv",
    value_column="synthetic_supply_mt",
    period="QS",
    lag_column="lag_4",
    lag_periods=4,
    lag_months=12,
    observed_count=8,
    forecast_count=4,
    unit="MT",
)
PRICE = ComponentSpec(
    name="price",
    source_file="red_onion_price_source.csv",
    value_column="synthetic_price_php_per_kg",
    period="MS",
    lag_column="lag_12",
    lag_periods=12,
    lag_months=12,
    observed_count=12,
    forecast_count=12,
    unit="PHP/kg",
)


def _require_columns(frame: pd.DataFrame, spec: ComponentSpec) -> None:
    required = {"commodity", "geolocation", "date", "status", spec.value_column}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{spec.source_file}: missing columns {sorted(missing)}")


def _validate_source(frame: pd.DataFrame, spec: ComponentSpec) -> pd.DataFrame:
    _require_columns(frame, spec)
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data[spec.value_column] = pd.to_numeric(data[spec.value_column], errors="raise")

    if set(data["commodity"]) != {_COMMODITY}:
        raise ValueError(f"{spec.source_file}: commodity must be {_COMMODITY!r}")
    if set(data["geolocation"]) != set(PROVINCES):
        raise ValueError(f"{spec.source_file}: provinces must exactly match {PROVINCES}")
    if data.duplicated(["geolocation", "date"]).any():
        raise ValueError(f"{spec.source_file}: duplicate province/date rows")
    if not data[spec.value_column].notna().all() or (data[spec.value_column] < 0).any():
        raise ValueError(f"{spec.source_file}: values must be non-negative numeric values")
    if not set(data["status"]).issubset({_HISTORICAL, _FORECAST}):
        raise ValueError(f"{spec.source_file}: unsupported status")

    for province, group in data.groupby("geolocation", sort=False):
        group = group.sort_values("date")
        observed = group[group["status"] == _HISTORICAL]
        future = group[group["status"] == _FORECAST]
        if len(observed) != spec.observed_count or len(future) != spec.forecast_count:
            raise ValueError(f"{spec.source_file}: unexpected row count for {province}")
        if observed["date"].max() >= future["date"].min():
            raise ValueError(f"{spec.source_file}: future dates must follow observations for {province}")
        expected = pd.date_range(group["date"].min(), periods=len(group), freq=spec.period)
        if not group["date"].reset_index(drop=True).equals(pd.Series(expected)):
            raise ValueError(f"{spec.source_file}: dates are not contiguous {spec.period} rows for {province}")
    return data.sort_values(["geolocation", "date"]).reset_index(drop=True)


def prepare_component(source_dir: Path, spec: ComponentSpec) -> pd.DataFrame:
    """Create the minimum prepared runtime schema for one synthetic component."""
    source = pd.read_csv(source_dir / spec.source_file)
    data = _validate_source(source, spec)
    data[spec.lag_column] = data.groupby("geolocation", sort=False)[spec.value_column].shift(
        spec.lag_periods
    )
    data["target"] = data[spec.value_column].where(data["status"] == _HISTORICAL)

    future = data["status"] == _FORECAST
    if data.loc[future, spec.lag_column].isna().any():
        raise ValueError(f"{spec.source_file}: future rows need {spec.lag_column}")

    return data[["geolocation", "date", "target", spec.lag_column]]


def _bundle(spec: ComponentSpec, prepared: pd.DataFrame) -> dict:
    history_tail = prepared[prepared["target"].notna()].tail(spec.observed_count).to_dict("records")
    return {
        "schema_version": "3.2",
        "created_utc": "2026-09-09T00:00:00Z",
        "commodity": _COMMODITY,
        "model_id": f"red_onion_{spec.name}_synthetic_mvp_v1",
        "kind": spec.name,
        "strategy": "seasonal_naive",
        "model": None,
        "features": [],
        "seasonal_period": spec.lag_periods,
        "metrics": {},
        "baseline_metrics": {},
        "improvement_vs_naive_pct": 0.0,
        "verdict": "CAUTION",
        "reason": "Synthetic MVP seasonal-naive proof-of-functioning artifact.",
        "limitations": [
            f"Synthetic MVP {spec.name} data for proof-of-functioning concept.",
        ],
        "history_tail": history_tail,
    }


def build(source_dir: Path = SOURCE_DIR, artifacts_dir: Path = ARTIFACTS_DIR) -> dict[str, pd.DataFrame]:
    """Write canonical prepared artifacts and model-free metadata bundles."""
    outputs: dict[str, pd.DataFrame] = {}
    for spec in (SUPPLY, PRICE):
        prepared = prepare_component(source_dir, spec)
        prepared_dir = artifacts_dir / "prepared"
        component_dir = artifacts_dir / spec.name
        prepared_dir.mkdir(parents=True, exist_ok=True)
        component_dir.mkdir(parents=True, exist_ok=True)
        prepared.to_csv(prepared_dir / f"red_onion_{spec.name}_features.csv", index=False)
        joblib.dump(_bundle(spec, prepared), component_dir / "red_onion.joblib")
        outputs[spec.name] = prepared

        observed = int(prepared["target"].notna().sum())
        future = int(prepared["target"].isna().sum())
        print(
            f"{spec.name}: {len(prepared)} rows; {observed} observed, {future} future; "
            f"{spec.lag_column} seasonal-naive fallback; unit {spec.unit}."
        )
    return outputs


if __name__ == "__main__":
    build()

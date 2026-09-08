"""Catalog, outlook, and evidence logic, decoupled from FastAPI/Pydantic.

Mirrors how `rag/pipeline.py` returns plain dataclasses that the API router
adapts into response schemas, keeping `ml/` free of a web-framework
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ml.forecasting.artifact_registry import ArtifactRegistry, slugify_commodity
from ml.forecasting.domain import COMMODITIES, COMPONENTS, PROVINCES

INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

RESOLUTION_NOTE = (
    "Analytics are province-resolution; this is not a municipality-level forecast."
)

# How much observed history to return per component (points, oldest -> newest).
_OBSERVED_TAIL = {"demand": 8, "supply": 8, "price": 12}
_FORECAST_HORIZON = 3

_UNIT = {
    "demand": "index (base~100)",
    "supply": "MT",
    "price": "PHP/kg",
}
_FREQUENCY = {"demand": "quarterly", "supply": "quarterly", "price": "monthly"}
_SEASONAL_LAG_COL = {"supply": "lag_4", "price": "lag_12"}
_CONFIDENCE_FROM_VERDICT = {"PASS": "HIGH", "CAUTION": "MODERATE"}


@dataclass(frozen=True)
class CommodityProvincePair:
    commodity: str
    province: str


@dataclass(frozen=True)
class CatalogPayload:
    commodities: tuple[str, ...]
    provinces: tuple[str, ...]
    pairs: tuple[CommodityProvincePair, ...]


@dataclass(frozen=True)
class OutlookComponentPayload:
    verdict: str
    observed: list[dict] | None = None
    forecast: list[dict] | None = None
    unit: str | None = None
    frequency: str | None = None
    confidence: str | None = None
    source: str | None = None
    data_as_of: str | None = None
    label: str | None = None
    limitations: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


@dataclass(frozen=True)
class OpportunityPayload:
    verdict: str
    score: float | None = None
    classification: str | None = None


@dataclass(frozen=True)
class OutlookPayload:
    commodity: str
    province: str
    resolution_note: str
    demand: OutlookComponentPayload
    supply: OutlookComponentPayload
    price: OutlookComponentPayload
    opportunity: OpportunityPayload


@dataclass(frozen=True)
class EvidenceComponentPayload:
    commodity: str
    component: str
    verdict: str
    target: str | None = None
    model: str | None = None
    reason: str | None = None
    frequency: str | None = None
    province_resolution: str = "province"
    source: str | None = None
    schema_version: str | None = None
    metrics: dict = field(default_factory=dict)
    baseline: dict = field(default_factory=dict)
    province_holdout: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _insufficient_opportunity() -> OpportunityPayload:
    return OpportunityPayload(verdict=INSUFFICIENT_DATA)


def _iso(value) -> str:
    ts = pd.Timestamp(value)
    return ts.date().isoformat()


def _points(frame: pd.DataFrame, value_col: str) -> list[dict]:
    return [
        {"period": _iso(row["date"]), "value": float(row[value_col])}
        for _, row in frame.iterrows()
        if pd.notna(row[value_col])
    ]


class ForecastService:
    """Answers catalog / outlook / evidence queries against a cached registry."""

    def __init__(self, registry: ArtifactRegistry) -> None:
        self._registry = registry

    def catalog(self) -> CatalogPayload:
        pairs = tuple(
            CommodityProvincePair(commodity=commodity, province=province)
            for commodity in COMMODITIES
            for province in PROVINCES
        )
        return CatalogPayload(commodities=COMMODITIES, provinces=PROVINCES, pairs=pairs)

    def outlook(self, commodity: str, province: str) -> OutlookPayload:
        demand = self._demand_component(commodity, province)
        supply = self._series_component(commodity, "supply", province)
        price = self._series_component(commodity, "price", province)

        return OutlookPayload(
            commodity=commodity,
            province=province,
            resolution_note=RESOLUTION_NOTE,
            demand=demand,
            supply=supply,
            price=price,
            opportunity=_insufficient_opportunity(),  # Sprint 2b
        )

    # -- demand ----------------------------------------------------------

    def _demand_component(self, commodity: str, province: str) -> OutlookComponentPayload:
        meta = self._registry.get(commodity, "demand")
        slug = slugify_commodity(commodity)

        observed = _filter(self._registry.demand_pressure_observed, slug, province)
        forecast = _filter(self._registry.demand_pressure_forecast, slug, province)

        if observed.empty and forecast.empty:
            verdict = meta.verdict if meta is not None else INSUFFICIENT_DATA
            return OutlookComponentPayload(
                verdict=verdict,
                label=meta.label if meta else None,
                limitations=list(meta.limitations) if meta else [],
                metrics=dict(meta.metrics) if meta else {},
            )

        observed_points = _points(observed.tail(_OBSERVED_TAIL["demand"]), "demand_pressure_index")
        forecast_points = _points(
            forecast.head(_FORECAST_HORIZON), "estimated_demand_pressure_index"
        )

        confidence = None
        if not forecast.empty and "confidence" in forecast.columns:
            raw = str(forecast.iloc[0]["confidence"]).lower()
            confidence = "MODERATE" if "moderate" in raw else "NONE"

        data_as_of = _iso(observed.iloc[-1]["date"]) if not observed.empty else None

        return OutlookComponentPayload(
            verdict=meta.verdict if meta is not None else "INDICATIVE_PROXY",
            observed=observed_points or None,
            forecast=forecast_points or None,
            unit=_UNIT["demand"],
            frequency=_FREQUENCY["demand"],
            confidence=confidence,
            source="demand_pressure_index",
            data_as_of=data_as_of,
            label=meta.label if meta else None,
            limitations=list(meta.limitations) if meta else [],
            metrics=dict(meta.metrics) if meta else {},
        )

    # -- supply / price -------------------------------------------------

    def _series_component(
        self, commodity: str, component: str, province: str
    ) -> OutlookComponentPayload:
        meta = self._registry.get(commodity, component)
        verdict = meta.verdict if meta is not None else INSUFFICIENT_DATA
        if verdict == INSUFFICIENT_DATA:
            return OutlookComponentPayload(
                verdict=INSUFFICIENT_DATA,
                limitations=list(meta.limitations) if meta else [],
            )

        table = self._registry.feature_table(commodity, component)
        if table is None or "geolocation" not in table.columns:
            return OutlookComponentPayload(verdict=INSUFFICIENT_DATA)

        rows = table[table["geolocation"] == province].sort_values("date")
        observed_rows = rows[rows["target"].notna()]
        if observed_rows.empty:
            return OutlookComponentPayload(verdict=INSUFFICIENT_DATA)

        last_observed = observed_rows.iloc[-1]["date"]
        future_rows = rows[rows["target"].isna() & (rows["date"] > last_observed)]

        forecast_points, source = self._forecast_rows(
            commodity, component, future_rows.head(_FORECAST_HORIZON * 2)
        )

        confidence = _CONFIDENCE_FROM_VERDICT.get(verdict, "NONE")
        return OutlookComponentPayload(
            verdict=verdict,
            observed=_points(observed_rows.tail(_OBSERVED_TAIL[component]), "target") or None,
            forecast=forecast_points[:_FORECAST_HORIZON] or None,
            unit=_UNIT[component],
            frequency=_FREQUENCY[component],
            confidence=confidence,
            source=source,
            data_as_of=_iso(last_observed),
            limitations=list(meta.limitations) if meta else [],
            metrics=dict(meta.metrics) if meta else {},
        )

    def _forecast_rows(
        self, commodity: str, component: str, future_rows: pd.DataFrame
    ) -> tuple[list[dict], str | None]:
        if future_rows.empty:
            return [], None

        bundle = self._registry.model_bundle(commodity, component)
        model = bundle.get("model") if bundle else None

        if model is not None:
            features = list(bundle.get("features", []))
            missing = [f for f in features if f not in future_rows.columns]
            if not missing:
                preds = model.predict(future_rows[features])
                points = [
                    {"period": _iso(row["date"]), "value": float(pred)}
                    for (_, row), pred in zip(future_rows.iterrows(), preds, strict=False)
                ]
                strategy = bundle.get("strategy") or "model"
                return points, f"learned_model:{strategy}"

        lag_col = _SEASONAL_LAG_COL[component]
        if lag_col not in future_rows.columns:
            return [], None
        naive = future_rows[future_rows[lag_col].notna()]
        return _points(naive, lag_col), "seasonal_naive"

    # -- evidence ------------------------------------------------------

    def evidence(self) -> list[EvidenceComponentPayload]:
        methodology = self._registry.methodology
        out: list[EvidenceComponentPayload] = []
        for commodity in COMMODITIES:
            for component in COMPONENTS:
                out.append(self._evidence_component(commodity, component, methodology))
        return out

    def _evidence_component(
        self, commodity: str, component: str, methodology: dict
    ) -> EvidenceComponentPayload:
        meta = self._registry.get(commodity, component)
        method = methodology.get(component, {}) if isinstance(methodology, dict) else {}

        if meta is None:
            return EvidenceComponentPayload(
                commodity=commodity,
                component=component,
                verdict=INSUFFICIENT_DATA,
                target=method.get("target"),
                frequency=_FREQUENCY[component],
            )

        source = None
        if meta.selected_model:
            source = (
                "seasonal_naive"
                if meta.selected_model == "seasonal_naive"
                else "learned_model"
            )
        if component == "demand":
            source = "fies_cross_sectional_estimator"

        return EvidenceComponentPayload(
            commodity=commodity,
            component=component,
            verdict=meta.verdict,
            target=meta.target or method.get("target"),
            model=meta.selected_model,
            reason=meta.reason,
            frequency=_FREQUENCY[component],
            source=source,
            schema_version=meta.schema_version,
            metrics=dict(meta.metrics),
            baseline=self._baseline_metrics(commodity, component),
            province_holdout=list(meta.province_holdout),
            limitations=list(meta.limitations),
        )

    def _baseline_metrics(self, commodity: str, component: str) -> dict:
        frame = self._registry.report(f"{component}_model_metrics")
        if frame is None:
            return {}
        slug = slugify_commodity(commodity)
        rows = frame[(frame["commodity"] == slug) & (frame["model"] == "seasonal_naive")]
        if rows.empty:
            return {}
        row = rows.iloc[0].to_dict()
        keys = ("sMAPE", "MASE", "WAPE", "RMSE")
        return {k: float(row[k]) for k in keys if k in row and pd.notna(row[k])}


def _filter(frame: pd.DataFrame, slug: str, province: str) -> pd.DataFrame:
    """Rows for one commodity/province, sorted by date. Empty frame when the
    series is absent (e.g. no prepared table was loaded)."""
    if frame.empty or not {"commodity", "province", "date"} <= set(frame.columns):
        return pd.DataFrame(columns=["commodity", "province", "date"])
    subset = frame[(frame["commodity"] == slug) & (frame["province"] == province)]
    return subset.sort_values("date")

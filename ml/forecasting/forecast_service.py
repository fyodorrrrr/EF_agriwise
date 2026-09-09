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
from ml.forecasting.opportunity import OpportunityScorer

_CONFIDENCE_SCORE = {"HIGH": 100.0, "MODERATE": 60.0, "NONE": 0.0}

INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

RESOLUTION_NOTE = (
    "Analytics are province-resolution; this is not a municipality-level forecast."
)

# How much observed history to return per component (points, oldest -> newest).
_OBSERVED_TAIL = {"demand": 8, "supply": 8, "price": 12}
_FORECAST_HORIZON = 4

# Raw rows needed from `_series_component` to cover _FORECAST_HORIZON quarters.
# Supply is already quarterly; price is monthly, so it needs 3x as many rows
# to reach the same number of quarters once the frontend buckets it.
_PERIODS_PER_HORIZON = {"supply": _FORECAST_HORIZON, "price": _FORECAST_HORIZON * 3}

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
    shared_quarter: str | None = None
    breakdown: dict = field(default_factory=dict)
    weights_used: dict = field(default_factory=dict)


@dataclass(frozen=True)
class OutlookPayload:
    commodity: str
    province: str
    resolution_note: str
    demand: OutlookComponentPayload
    supply: OutlookComponentPayload
    price: OutlookComponentPayload
    opportunity: OpportunityPayload


_DISCLAIMERS = (
    "Estimated Demand Proxy is a FIES expenditure-category index, not observed "
    "commodity consumption and not metric-tonne demand.",
    "Opportunity is a peer-relative decision-support score across the five "
    "CALABARZON provinces — not a causal finding and not a physical supply gap.",
    "Forecasts use the model that earned the component verdict, or a "
    "seasonal-naive fallback identified in `source`. Confidence intervals are "
    "not published because the artifacts do not provide them.",
    "Analytics are province-resolution; a municipality selection resolves to "
    "its province.",
)


@dataclass(frozen=True)
class MethodologyPayload:
    schema_version: str | None
    demand: dict
    supply: dict
    price: dict
    opportunity: dict
    commodity_flow: dict
    disclaimers: list[str]


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
            opportunity=self._opportunity(commodity, province),
        )

    # -- demand ----------------------------------------------------------

    def _demand_component(self, commodity: str, province: str) -> OutlookComponentPayload:
        if commodity == "Red Onion":
            physical = self._red_onion_physical_demand_component(province)
            if physical is not None:
                return physical

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

    def _red_onion_physical_demand_component(
        self, province: str
    ) -> OutlookComponentPayload | None:
        table = self._registry.red_onion_physical_demand
        required = {"province", "date", "target", "hfce_status"}
        if table.empty or not required <= set(table.columns):
            return None

        rows = table[table["province"] == province].sort_values("date")
        observed = rows[rows["hfce_status"] == "OBSERVED"]
        forecast = rows[rows["hfce_status"] == "FORECAST"]
        if observed.empty or forecast.empty:
            return None

        return OutlookComponentPayload(
            verdict="INDICATIVE_PROXY",
            observed=_points(observed.tail(_OBSERVED_TAIL["demand"]), "target"),
            forecast=_points(forecast.head(_FORECAST_HORIZON), "target"),
            unit="MT",
            frequency="quarterly",
            confidence="MODERATE",
            source="psa_sua_population_hfce_denton",
            data_as_of=_iso(observed.iloc[-1]["date"]),
            label="Estimated physical demand (PSA proxy)",
            limitations=[
                "National PSA Onion per-capita availability is applied to each province; "
                "this is not observed provincial consumption.",
                "Quarterly timing uses broad food HFCE and is benchmarked to annual PSA controls.",
            ],
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

        periods = _PERIODS_PER_HORIZON[component]
        forecast_points, source = self._forecast_rows(
            commodity, component, future_rows.head(periods * 2)
        )

        confidence = _CONFIDENCE_FROM_VERDICT.get(verdict, "NONE")
        return OutlookComponentPayload(
            verdict=verdict,
            observed=_points(observed_rows.tail(_OBSERVED_TAIL[component]), "target") or None,
            forecast=forecast_points[:periods] or None,
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

    # -- opportunity --------------------------------------------------

    def _opportunity(self, commodity: str, province: str) -> OpportunityPayload:
        scorer = OpportunityScorer(self._registry.opportunity_config)

        per_province: dict[str, dict] = {}
        for prov in PROVINCES:
            demand = self._demand_component(commodity, prov)
            supply = self._series_component(commodity, "supply", prov)
            price = self._series_component(commodity, "price", prov)
            if INSUFFICIENT_DATA in (demand.verdict, supply.verdict, price.verdict):
                return _insufficient_opportunity()
            per_province[prov] = {
                "demand": _quarterly(demand),
                "supply": _quarterly(supply),
                "price": _quarterly(price, monthly=True),
                "confidence": _mean_confidence(demand, supply, price),
            }

        shared = _shared_quarter(per_province)
        if shared is None:
            return _insufficient_opportunity()

        peers = {
            prov: {
                "demand": maps["demand"].get(shared),
                "supply": maps["supply"].get(shared),
                "price": maps["price"].get(shared),
                "confidence": maps["confidence"],
            }
            for prov, maps in per_province.items()
        }
        result = scorer.score(province, peers)
        if result.score is None:
            return _insufficient_opportunity()
        return OpportunityPayload(
            verdict=result.verdict,
            score=result.score,
            classification=result.classification,
            shared_quarter=shared,
            breakdown=result.breakdown,
            weights_used=result.weights_used,
        )

    # -- methodology --------------------------------------------------

    def methodology(self) -> MethodologyPayload:
        m = self._registry.methodology or {}
        return MethodologyPayload(
            schema_version=m.get("version"),
            demand=dict(m.get("demand", {})),
            supply=dict(m.get("supply", {})),
            price=dict(m.get("price", {})),
            opportunity=dict(self._registry.opportunity_config),
            commodity_flow=dict(self._registry.commodity_flow_methodology),
            disclaimers=list(_DISCLAIMERS),
        )

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
        if commodity == "Red Onion" and component == "demand":
            physical = self._registry.red_onion_physical_demand
            if not physical.empty:
                return EvidenceComponentPayload(
                    commodity=commodity,
                    component=component,
                    verdict="INDICATIVE_PROXY",
                    target="quarterly_demand_mt",
                    model="annual_pcc_linear_trend + HFCE recent_yoy_growth + Denton",
                    reason="PSA national per-capita availability is spatially allocated to provinces.",
                    frequency="quarterly",
                    source="psa_sua_population_hfce_denton",
                    limitations=[
                        "National PSA Onion per-capita availability is not observed provincial consumption.",
                        "Broad food HFCE supplies quarterly timing only.",
                    ],
                )

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


def _quarter_start(period: str) -> str:
    ts = pd.Timestamp(period)
    return f"{ts.year:04d}-{((ts.month - 1) // 3) * 3 + 1:02d}-01"


def _quarterly(component: OutlookComponentPayload, *, monthly: bool = False) -> dict[str, float]:
    """{quarter-start ISO date -> value}. Monthly series (price) average the
    months that fall in each quarter."""
    points = (component.observed or []) + (component.forecast or [])
    if not monthly:
        return {p["period"]: float(p["value"]) for p in points}
    buckets: dict[str, list[float]] = {}
    for p in points:
        buckets.setdefault(_quarter_start(p["period"]), []).append(float(p["value"]))
    return {q: sum(v) / len(v) for q, v in buckets.items()}


def _mean_confidence(*components: OutlookComponentPayload) -> float:
    scores = [_CONFIDENCE_SCORE.get(c.confidence or "NONE", 0.0) for c in components]
    return sum(scores) / len(scores) if scores else 0.0


def _shared_quarter(per_province: dict[str, dict]) -> str | None:
    """Most recent quarter present in demand, supply, and price for every
    province."""
    common: set[str] | None = None
    for maps in per_province.values():
        quarters = set(maps["demand"]) & set(maps["supply"]) & set(maps["price"])
        common = quarters if common is None else (common & quarters)
    if not common:
        return None
    return max(common)


def _filter(frame: pd.DataFrame, slug: str, province: str) -> pd.DataFrame:
    """Rows for one commodity/province, sorted by date. Empty frame when the
    series is absent (e.g. no prepared table was loaded)."""
    if frame.empty or not {"commodity", "province", "date"} <= set(frame.columns):
        return pd.DataFrame(columns=["commodity", "province", "date"])
    subset = frame[(frame["commodity"] == slug) & (frame["province"] == province)]
    return subset.sort_values("date")

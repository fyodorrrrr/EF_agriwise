"""Small deterministic market-advisory layer over existing AgriWise services."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from markets.ranking import rank_markets
from markets.registry import MarketRegistry
from ml.forecasting.domain import COMMODITIES
from ml.forecasting.forecast_service import ForecastService


def _quarter(period: str) -> str:
    stamp = pd.Timestamp(period)
    return f"{stamp.year}-Q{(stamp.month - 1) // 3 + 1}"


def _quarter_start(period: str) -> str:
    stamp = pd.Timestamp(period)
    return f"{stamp.year:04d}-{((stamp.month - 1) // 3) * 3 + 1:02d}-01"


def _points(component) -> list[dict]:
    return list(component.observed or []) + list(component.forecast or [])


def _quarterly_values(component) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for point in _points(component):
        key = _quarter_start(point["period"])
        buckets.setdefault(key, []).append(float(point["value"]))
    return {key: sum(values) / len(values) for key, values in buckets.items()}


def _value_and_growth(
    component, period: str, *, monthly: bool = False
) -> tuple[float | None, float | None]:
    values = (
        _quarterly_values(component)
        if monthly
        else {point["period"]: float(point["value"]) for point in _points(component)}
    )
    current = values.get(period)
    if current is None:
        return None, None
    previous = (pd.Timestamp(period) - pd.DateOffset(months=3)).strftime("%Y-%m-%d")
    prior = values.get(previous)
    if prior is None or prior == 0:
        return current, None
    return current, round((current - prior) / prior * 100, 2)


def _component(component, value: float | None) -> dict:
    return {
        "value": round(value, 2) if value is not None else None,
        "unit": component.unit,
        "frequency": component.frequency,
        "verdict": component.verdict,
        "confidence": component.confidence,
        "source": component.source,
        "limitations": list(component.limitations),
    }


def _advisory_type(classification: str | None, price_growth: float | None) -> tuple[str, int]:
    if classification == "HIGH_OPPORTUNITY":
        return "OPPORTUNITY", 80
    if classification == "UNDERSUPPLY_LEANING":
        return "OPPORTUNITY", 70
    if classification == "SEVERE_OVERSUPPLY":
        return "RISK", 85
    if classification == "OVERSUPPLY_LEANING":
        return "RISK", 70
    if price_growth is not None and abs(price_growth) >= 10:
        return "PRICE_UPDATE", 60
    return "MARKET_WATCH", 50


def _wording(
    commodity: str, province: str, advisory_type: str, classification: str | None
) -> tuple[str, str, str]:
    name = commodity.lower()
    if advisory_type == "OPPORTUNITY":
        headline = f"{commodity} market conditions may present an opportunity in {province}"
        summary = (
            "AgriWise's peer-relative opportunity signal indicates conditions worth monitoring "
            "against other CALABARZON provinces."
        )
    elif advisory_type == "RISK":
        headline = f"{commodity} supply conditions need attention in {province}"
        summary = (
            "AgriWise's peer-relative signal indicates that relatively greater supply may put "
            "market conditions under pressure."
        )
    elif advisory_type == "PRICE_UPDATE":
        headline = f"{commodity} prices are worth watching in {province}"
        summary = (
            "The latest comparable quarterly price average changed materially from the "
            "previous quarter."
        )
    else:
        headline = f"{commodity} market conditions remain worth watching in {province}"
        summary = (
            "Available demand, supply, price, and opportunity indicators do not point to a "
            "stronger single advisory at this time."
        )
    consideration = (
        f"Farmers planning {name} production may consider monitoring local prices, "
        "production costs, "
        "and available market locations before making planting or marketing decisions."
    )
    return headline, summary, consideration


@dataclass
class AdvisoryService:
    forecast_service: ForecastService
    market_registry: MarketRegistry

    def advisories(self, province: str) -> dict:
        rows = [self._advisory(commodity, province) for commodity in COMMODITIES]
        rows.sort(key=lambda row: row["priority"], reverse=True)
        period = next((row["period"] for row in rows if row["period"]), None)
        counts = {
            kind: sum(row["advisory_type"] == kind for row in rows)
            for kind in ("OPPORTUNITY", "MARKET_WATCH", "RISK", "PRICE_UPDATE", "MARKET_ACCESS")
        }
        return {"province": province, "period": period, "market_brief": counts, "advisories": rows}

    def _advisory(self, commodity: str, province: str) -> dict:
        outlook = self.forecast_service.outlook(commodity, province)
        period = outlook.opportunity.shared_quarter
        if period is None:
            candidates = [
                point["period"]
                for component in (outlook.demand, outlook.supply, outlook.price)
                for point in _points(component)
            ]
            period = max(candidates) if candidates else None

        demand_value, demand_growth = (
            _value_and_growth(outlook.demand, period) if period else (None, None)
        )
        supply_value, supply_growth = (
            _value_and_growth(outlook.supply, period) if period else (None, None)
        )
        price_value, price_growth = (
            _value_and_growth(outlook.price, period, monthly=True) if period else (None, None)
        )
        physical_gap = gap_ratio = None
        if (
            outlook.demand.unit == outlook.supply.unit == "MT"
            and demand_value is not None
            and supply_value is not None
        ):
            physical_gap = round(demand_value - supply_value, 2)
            gap_ratio = round(physical_gap / demand_value, 4) if demand_value else None

        advisory_type, priority = _advisory_type(outlook.opportunity.classification, price_growth)
        headline, summary, consideration = _wording(
            commodity, province, advisory_type, outlook.opportunity.classification
        )
        limitations = list(
            dict.fromkeys(
                outlook.demand.limitations + outlook.supply.limitations + outlook.price.limitations
            )
        )
        supported = sum(
            component.verdict != "INSUFFICIENT_DATA"
            for component in (outlook.demand, outlook.supply, outlook.price)
        )
        markets = [
            {
                "market_id": item.market.market_id,
                "market_name": item.market.market_name,
                "municipality": item.market.municipality,
                "market_type": item.market.market_type,
                "coordinate_confidence": item.market.coordinate_confidence,
                "distance_km": item.distance_km,
            }
            for item in rank_markets(
                self.market_registry, province=province, supported_analytics=supported
            )[:3]
        ]
        confidence = (
            "HIGH"
            if all(c.confidence == "HIGH" for c in (outlook.demand, outlook.supply, outlook.price))
            else "MODERATE"
            if any(
                c.confidence == "MODERATE" for c in (outlook.demand, outlook.supply, outlook.price)
            )
            else "NONE"
        )
        return {
            "commodity": commodity,
            "province": province,
            "period": _quarter(period) if period else None,
            "advisory_type": advisory_type,
            "priority": priority,
            "headline": headline,
            "summary": summary,
            "farmer_consideration": consideration,
            "opportunity": {
                "score": outlook.opportunity.score,
                "classification": outlook.opportunity.classification,
            },
            "signals": {
                "demand_growth_pct": demand_growth,
                "supply_growth_pct": supply_growth,
                "price_growth_pct": price_growth,
                "physical_gap": physical_gap,
                "gap_ratio": gap_ratio,
            },
            "demand": _component(outlook.demand, demand_value),
            "supply": _component(outlook.supply, supply_value),
            "price": _component(outlook.price, price_value),
            "markets": markets,
            "confidence": confidence,
            "limitations": list(dict.fromkeys(limitations)),
        }

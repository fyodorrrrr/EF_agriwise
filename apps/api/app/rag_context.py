"""Resolve a bounded, deterministic analytics-context string for the chatbot.

Everything here comes from the trusted `ForecastService` — the client only
supplies commodity/province *selectors*, never numbers.
"""

from __future__ import annotations

from functools import lru_cache

from ml.forecasting.domain import COMMODITIES, PROVINCES
from ml.forecasting.forecast_service import ForecastService

_KINDS = (
    ("Demand (Estimated Demand Proxy, index)", "demand"),
    ("Supply (metric tonnes, quarterly)", "supply"),
    ("Price (PHP/kg, monthly)", "price"),
)


def _period_label(iso: str) -> str:
    """2026-07-01 -> 'Q3 2026' for quarter starts, else '2026-07'."""
    year, month, _ = iso.split("-")
    m = int(month)
    if m in (1, 4, 7, 10):
        return f"Q{(m - 1) // 3 + 1} {year}"
    return f"{year}-{month}"

# Farmer-facing wording for the raw backend verdict — mirrors
# apps/web/src/components/forecast/verdict.ts. INSUFFICIENT_DATA is handled
# separately above, so it has no entry here.
_VERDICT_LABEL = {
    "PASS": "Good Forecast",
    "CAUTION": "Planning Estimate",
    "USABLE_PROXY": "Estimated Demand",
    "INDICATIVE_PROXY": "Demand Trend",
}


def build_analytics_context(
    service: ForecastService, commodity: str | None, province: str | None
) -> str | None:
    if commodity not in COMMODITIES or province not in PROVINCES:
        return None
    try:
        outlook = service.outlook(commodity, province)
    except Exception:
        return None

    lines = [
        f"Selection: {commodity} in {province} province. Analytics are "
        f"province-resolution, not municipality-level."
    ]
    for label, attr in _KINDS:
        component = getattr(outlook, attr)
        if component.verdict == "INSUFFICIENT_DATA":
            lines.append(f"- {label}: not available (insufficient data).")
            continue
        parts = [f"quality: {_VERDICT_LABEL[component.verdict]}"]
        if component.observed:
            last = component.observed[-1]
            parts.append(f"latest observed {last['value']:.1f} ({last['period']})")
        if component.forecast:
            series = ", ".join(
                f"{_period_label(p['period'])} {p['value']:.1f}" for p in component.forecast
            )
            parts.append(f"forecast by period [{series}] (source {component.source})")
        if component.confidence:
            parts.append(f"confidence {component.confidence}")
        lines.append(f"- {label}: " + "; ".join(parts))

    opp = outlook.opportunity
    if opp.verdict == "INSUFFICIENT_DATA":
        lines.append(
            "- Opportunity: not available (needs demand, supply and price for every "
            "province in a shared quarter)."
        )
    else:
        lines.append(
            f"- Opportunity: score {opp.score}/100 ({opp.classification}), shared "
            f"quarter {opp.shared_quarter}. This is a peer-relative decision-support "
            f"score, not a physical supply gap."
        )
    return "\n".join(lines)


def _opportunity_phrase(opp) -> str:
    if opp.verdict == "INSUFFICIENT_DATA" or opp.score is None:
        return "opportunity not available"
    return f"opportunity {opp.score:.0f}/100 ({opp.classification})"


def _grid_phrase(component, label: str, unit: str, fmt: str) -> str:
    """Concise: last observed + full forecast series, for the grid rows."""
    if component.verdict == "INSUFFICIENT_DATA" or not (
        component.observed or component.forecast
    ):
        return f"{label} not available"
    parts = []
    if component.observed:
        last = component.observed[-1]
        parts.append(f"{last['value']:{fmt}}{unit} observed ({_period_label(last['period'])})")
    if component.forecast:
        series = "; ".join(
            f"{_period_label(p['period'])} {p['value']:{fmt}}{unit}" for p in component.forecast
        )
        parts.append(f"forecast [{series}]")
    return f"{label} " + ", ".join(parts)


def _price_phrase(price) -> str:
    return _grid_phrase(price, "price", " PHP/kg", ".1f")


def _demand_phrase(demand) -> str:
    return _grid_phrase(demand, "demand proxy index", "", ".1f")


def _supply_phrase(supply) -> str:
    return _grid_phrase(supply, "supply", " MT", ".0f")


@lru_cache(maxsize=4)
def build_full_grid_context(service: ForecastService) -> str | None:
    """Every commodity x province outlook in one block, so the model can answer
    any cross-cut. Cached — the artifacts do not change during a server run."""
    rows: list[str] = []
    for commodity in COMMODITIES:
        for province in PROVINCES:
            try:
                outlook = service.outlook(commodity, province)
            except Exception:
                continue
            parts = [
                _demand_phrase(outlook.demand),
                _supply_phrase(outlook.supply),
                _price_phrase(outlook.price),
                _opportunity_phrase(outlook.opportunity),
            ]
            rows.append(f"- {commodity} / {province}: " + "; ".join(parts))

    if not rows:
        return None
    header = (
        "Full CALABARZON analytics grid, province-resolution. Demand is the Estimated "
        "Demand Proxy index (base around 100), not tonnage or consumption. Supply is "
        "metric tonnes, quarterly. Price is PHP/kg. Opportunity is a peer-relative "
        "decision-support score across the five provinces, not a physical supply gap or "
        "a profit prediction. \"not available\" means no estimate exists — do not guess one."
    )
    return "\n".join([header, *rows])

"""Resolve a bounded, deterministic analytics-context string for the chatbot.

Everything here comes from the trusted `ForecastService` — the client only
supplies commodity/province *selectors*, never numbers.
"""

from __future__ import annotations

from ml.forecasting.domain import COMMODITIES, PROVINCES
from ml.forecasting.forecast_service import ForecastService

_KINDS = (
    ("Demand (Estimated Demand Proxy, index)", "demand"),
    ("Supply (metric tonnes, quarterly)", "supply"),
    ("Price (PHP/kg, monthly)", "price"),
)


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
        parts = [f"verdict {component.verdict}"]
        if component.observed:
            last = component.observed[-1]
            parts.append(f"latest observed {last['value']:.1f} ({last['period']})")
        if component.forecast:
            nxt = component.forecast[-1]
            parts.append(
                f"forecast {nxt['value']:.1f} ({nxt['period']}, source {component.source})"
            )
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

"""Peer-relative opportunity scoring.

Every weight, direction, and policy line comes from
``ml/artifacts/config/opportunity_scoring_config.json`` (surfaced by the
registry as ``registry.opportunity_config``) — nothing here is hardcoded
except the 0-100 normalization method and the classification bands.

The score is a decision-support signal that ranks the five CALABARZON
provinces against each other for one commodity at one shared quarter. It is
not a learned target and not a physical supply gap; FIES index points are
never subtracted from supply metric tons.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

# score band -> classification (checked high to low)
_BANDS: tuple[tuple[float, str], ...] = (
    (75.0, "HIGH_OPPORTUNITY"),
    (60.0, "UNDERSUPPLY_LEANING"),
    (40.0, "BALANCED"),
    (25.0, "OVERSUPPLY_LEANING"),
    (0.0, "SEVERE_OVERSUPPLY"),
)

# config component key -> (input field, invert?). ``forecast_confidence_index``
# is already an absolute 0-100 value, so it is not rank-normalized.
_INPUT_FIELD = {
    "demand_pressure_index": ("demand", False),
    "supply_gap_or_scarcity_index": ("supply", True),
    "price_opportunity_index": ("price", False),
    "forecast_confidence_index": ("confidence", False),
}
_ABSOLUTE = {"forecast_confidence_index"}


@dataclass(frozen=True)
class OpportunityResult:
    verdict: str
    score: float | None = None
    classification: str | None = None
    shared_quarter: str | None = None
    breakdown: dict = field(default_factory=dict)
    weights_used: dict = field(default_factory=dict)


def _classify(score: float) -> str:
    for threshold, label in _BANDS:
        if score >= threshold:
            return label
    return _BANDS[-1][1]


def _rank_pct(values: dict[str, float], *, invert: bool) -> dict[str, float]:
    series = pd.Series(values, dtype="float64")
    if invert:
        series = -series
    n = len(series)
    if n <= 1:
        return {k: 50.0 for k in values}
    ranks = series.rank(method="average")
    return {k: float((ranks[k] - 1) / (n - 1) * 100.0) for k in values}


class OpportunityScorer:
    def __init__(self, config: dict | None) -> None:
        self._components: dict = (config or {}).get("components", {})

    def score(self, target_province: str, peers: dict[str, dict]) -> OpportunityResult:
        """``peers``: ``{province: {"demand", "supply", "price", "confidence"}}``
        for all five provinces, every value present. The caller enforces
        completeness and picks the shared quarter."""
        if target_province not in peers or not self._components:
            return OpportunityResult(verdict=INSUFFICIENT_DATA)

        active: list[str] = []
        for key, spec in self._components.items():
            if spec.get("optional") and key not in _INPUT_FIELD:
                continue
            if key not in _INPUT_FIELD:
                continue
            field_name, _ = _INPUT_FIELD[key]
            if any(p.get(field_name) is None for p in peers.values()):
                if spec.get("optional"):
                    continue
                return OpportunityResult(verdict=INSUFFICIENT_DATA)
            active.append(key)

        if not active:
            return OpportunityResult(verdict=INSUFFICIENT_DATA)

        total_weight = sum(float(self._components[k].get("weight", 0.0)) for k in active)
        if total_weight <= 0:
            return OpportunityResult(verdict=INSUFFICIENT_DATA)

        weights_used = {
            k: float(self._components[k].get("weight", 0.0)) / total_weight for k in active
        }

        breakdown: dict[str, dict] = {}
        score = 0.0
        for key in active:
            field_name, invert = _INPUT_FIELD[key]
            raw_by_prov = {p: peers[p][field_name] for p in peers}
            if key in _ABSOLUTE:
                normalized = {p: float(v) for p, v in raw_by_prov.items()}
            else:
                normalized = _rank_pct(raw_by_prov, invert=invert)
            component_score = normalized[target_province]
            score += weights_used[key] * component_score
            breakdown[key] = {
                "raw": float(raw_by_prov[target_province]),
                "score": round(component_score, 2),
                "weight": round(weights_used[key], 4),
            }

        score = round(score, 2)
        return OpportunityResult(
            verdict="PASS",
            score=score,
            classification=_classify(score),
            breakdown=breakdown,
            weights_used={k: round(v, 4) for k, v in weights_used.items()},
        )

"""Catalog and outlook logic, decoupled from FastAPI/Pydantic.

Mirrors how `rag/pipeline.py` returns plain dataclasses that the API router
adapts into response schemas, keeping `ml/` free of a web-framework
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ml.forecasting.artifact_registry import ArtifactRegistry
from ml.forecasting.domain import COMMODITIES, COMPONENTS, PROVINCES

INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

RESOLUTION_NOTE = (
    "Analytics are province-resolution; this is not a municipality-level forecast."
)


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
    values: list[float] | None = None
    unit: str | None = None
    frequency: str | None = None
    confidence: str | None = None
    source: str | None = None
    data_as_of: str | None = None
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


def _insufficient_data_component() -> OutlookComponentPayload:
    return OutlookComponentPayload(verdict=INSUFFICIENT_DATA)


def _insufficient_data_opportunity() -> OpportunityPayload:
    return OpportunityPayload(verdict=INSUFFICIENT_DATA)


class ForecastService:
    """Answers catalog and outlook queries against a cached artifact registry."""

    def __init__(self, registry: ArtifactRegistry) -> None:
        self._registry = registry

    def catalog(self) -> CatalogPayload:
        # Catalog is "what's askable," not "what's answerable" — it must not
        # consult the registry, so it stays stable regardless of which
        # artifacts (if any) are loaded.
        pairs = tuple(
            CommodityProvincePair(commodity=commodity, province=province)
            for commodity in COMMODITIES
            for province in PROVINCES
        )
        return CatalogPayload(commodities=COMMODITIES, provinces=PROVINCES, pairs=pairs)

    def outlook(self, commodity: str, province: str) -> OutlookPayload:
        components: dict[str, OutlookComponentPayload] = {}
        for component in COMPONENTS:
            artifact = self._registry.get(commodity, component)
            if artifact is None:
                components[component] = _insufficient_data_component()
                continue
            # Reflects the artifact's own verdict/metrics/limitations. Forward-
            # looking value/date generation (predicted future quarters/months)
            # is a separate, not-yet-designed piece of work: `values`,
            # `unit`, `frequency`, `confidence`, `source`, and `data_as_of`
            # stay None until that lands.
            components[component] = OutlookComponentPayload(
                verdict=artifact.verdict,
                metrics=artifact.metrics,
                limitations=artifact.limitations,
            )

        # Missing any critical demand/supply/price input blocks opportunity
        # scoring entirely — with an empty registry every input is missing.
        opportunity = _insufficient_data_opportunity()

        return OutlookPayload(
            commodity=commodity,
            province=province,
            resolution_note=RESOLUTION_NOTE,
            demand=components["demand"],
            supply=components["supply"],
            price=components["price"],
            opportunity=opportunity,
        )

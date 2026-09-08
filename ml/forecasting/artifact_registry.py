"""Cached registry of trained forecasting artifacts.

Supply and price bundles live at ``<artifacts_dir>/<component>/<commodity_slug>.joblib``
and carry their own ``commodity`` key (Title Case). Demand bundles are keyed
on ``artifact_name`` instead (``rice`` / ``vegetable_shared`` / ``banana``);
the commodity -> demand-artifact mapping — including the one shared VEG
estimator that backs both Tomato and Red Onion — comes from
``<artifacts_dir>/config/commodity_demand_registry.json``. When that config is
absent the loader falls back to globbing ``demand/*.joblib`` and reading a
``commodity`` key, which keeps synthetic-bundle tests working.

`ArtifactRegistry.load` must work against a missing or empty directory: it
returns an empty registry rather than raising, so the API can start up and
serve `INSUFFICIENT_DATA` for every component until real artifacts land.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import joblib

from ml.forecasting.domain import COMMODITIES, COMPONENTS

logger = logging.getLogger("agriwise.forecast")

Component = Literal["demand", "supply", "price"]

_DEMAND_REGISTRY_REL = Path("config") / "commodity_demand_registry.json"


def slugify_commodity(commodity: str) -> str:
    return commodity.strip().lower().replace(" ", "_")


@dataclass(frozen=True)
class ArtifactMetadata:
    """Minimal metadata describing one loaded artifact bundle.

    Intentionally minimal: no schema-version or feature-list validation yet.
    Sprint 2a extends this once the full bundle (prepared/, config/, reports/)
    is wired in.
    """

    model_id: str
    commodity: str
    component: Component
    verdict: str
    metrics: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    label: str | None = None


class ArtifactRegistry:
    """Cached lookup of `(commodity, component) -> ArtifactMetadata`."""

    def __init__(self, artifacts_dir: Path) -> None:
        self._artifacts_dir = artifacts_dir
        self._bundles: dict[tuple[str, str], ArtifactMetadata] = {}
        self._diagnostics: list[str] = []

    @classmethod
    def load(cls, artifacts_dir: Path) -> ArtifactRegistry:
        registry = cls(artifacts_dir)

        if not artifacts_dir.exists():
            logger.warning(
                "forecast artifacts directory missing at %s; registry loads empty "
                "and every component reports INSUFFICIENT_DATA",
                artifacts_dir,
            )
            return registry

        demand_registry = registry._read_json(artifacts_dir / _DEMAND_REGISTRY_REL)

        for component in COMPONENTS:
            if component == "demand" and demand_registry:
                registry._load_demand_from_registry(demand_registry)
                continue
            component_dir = artifacts_dir / component
            if not component_dir.is_dir():
                continue
            for bundle_path in sorted(component_dir.glob("*.joblib")):
                registry._load_modeled_bundle(component, bundle_path)

        if registry.is_empty:
            logger.warning(
                "forecast artifacts directory %s contained no loadable bundles; "
                "registry loads empty",
                artifacts_dir,
            )

        return registry

    def _load_modeled_bundle(self, component: str, bundle_path: Path) -> None:
        """Load a supply/price bundle (or a legacy demand bundle carrying its
        own ``commodity`` key)."""
        try:
            bundle = joblib.load(bundle_path)
            commodity = str(bundle["commodity"])
            metadata = ArtifactMetadata(
                model_id=str(bundle["model_id"]),
                commodity=commodity,
                component=component,  # type: ignore[arg-type]
                verdict=str(bundle["verdict"]),
                metrics=dict(bundle.get("metrics", {})),
                limitations=list(bundle.get("limitations", [])),
            )
        except Exception:
            logger.warning(
                "failed to load artifact bundle %s; skipping", bundle_path, exc_info=True
            )
            self._diagnostics.append(f"{component}: failed to load {bundle_path.name}")
            return

        self._bundles[(metadata.commodity, component)] = metadata

    def _load_demand_from_registry(self, demand_registry: dict) -> None:
        """Resolve demand bundles via ``config/commodity_demand_registry.json``.

        Bundles are keyed on ``artifact_name`` (not ``commodity``) and one file
        (``vegetable_shared``) backs two commodities, so a shared joblib is
        loaded once and reused.
        """
        slug_to_commodity = {slugify_commodity(c): c for c in COMMODITIES}
        bundle_cache: dict[Path, dict] = {}

        for slug, entry in demand_registry.items():
            commodity = slug_to_commodity.get(slug)
            if commodity is None:
                self._diagnostics.append(f"demand: unknown commodity slug {slug!r} in registry")
                continue
            bundle_path = self._artifacts_dir / str(entry.get("artifact", ""))
            try:
                if bundle_path not in bundle_cache:
                    bundle_cache[bundle_path] = joblib.load(bundle_path)
                bundle = bundle_cache[bundle_path]
                metrics = bundle.get("metrics") or bundle.get("weighted_metrics") or {}
                metadata = ArtifactMetadata(
                    model_id=str(bundle["model_id"]),
                    commodity=commodity,
                    component="demand",
                    verdict=str(bundle["verdict"]),
                    metrics=dict(metrics),
                    limitations=list(bundle.get("limitations", [])),
                    label=entry.get("label"),
                )
            except Exception:
                logger.warning(
                    "failed to load demand bundle %s for %s; skipping",
                    bundle_path,
                    commodity,
                    exc_info=True,
                )
                self._diagnostics.append(
                    f"demand: failed to load {bundle_path.name} for {commodity}"
                )
                continue

            self._bundles[(commodity, "demand")] = metadata

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text())
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            logger.warning("failed to read artifact config %s; ignoring", path, exc_info=True)
            self._diagnostics.append(f"config: failed to read {path.name}")
            return {}

    def has(self, commodity: str, component: str) -> bool:
        return (commodity, component) in self._bundles

    def get(self, commodity: str, component: str) -> ArtifactMetadata | None:
        return self._bundles.get((commodity, component))

    @property
    def is_empty(self) -> bool:
        return not self._bundles

    @property
    def diagnostics(self) -> list[str]:
        """Human-readable notes about artifacts that were expected but skipped."""
        return list(self._diagnostics)

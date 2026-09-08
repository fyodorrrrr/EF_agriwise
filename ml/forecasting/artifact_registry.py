"""Cached registry of trained forecasting artifacts.

An artifact bundle is a joblib-serialized dict living at
``<artifacts_dir>/<component>/<commodity_slug>.joblib`` (component is one of
``demand``/``supply``/``price``; commodity_slug is the commodity name
lowercased with spaces replaced by underscores, e.g. "Red Onion" ->
"red_onion"). The bundle dict is expected to carry at least
``model_id``, ``verdict``, ``metrics``, and ``limitations`` keys; a ``model``
key (the trained estimator) is optional and not consulted here.

No artifacts are committed to this repository yet. `ArtifactRegistry.load`
must therefore work correctly against a missing or empty directory: it
returns an empty registry rather than raising, so the API can start up and
serve `INSUFFICIENT_DATA` for every component until real artifacts land.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import joblib

from ml.forecasting.domain import COMPONENTS

logger = logging.getLogger("agriwise.forecast")

Component = Literal["demand", "supply", "price"]


def slugify_commodity(commodity: str) -> str:
    return commodity.strip().lower().replace(" ", "_")


@dataclass(frozen=True)
class ArtifactMetadata:
    """Minimal metadata describing one loaded artifact bundle.

    Intentionally minimal: no schema-version or feature-list validation yet.
    Sprint 2/3 extend this once real artifacts exist.
    """

    model_id: str
    commodity: str
    component: Component
    verdict: str
    metrics: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)


class ArtifactRegistry:
    """Cached lookup of `(commodity, component) -> ArtifactMetadata`."""

    def __init__(self, artifacts_dir: Path) -> None:
        self._artifacts_dir = artifacts_dir
        self._bundles: dict[tuple[str, str], ArtifactMetadata] = {}

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

        for component in COMPONENTS:
            component_dir = artifacts_dir / component
            if not component_dir.is_dir():
                continue
            for bundle_path in sorted(component_dir.glob("*.joblib")):
                registry._load_bundle(component, bundle_path)

        if registry.is_empty:
            logger.warning(
                "forecast artifacts directory %s contained no loadable bundles; "
                "registry loads empty",
                artifacts_dir,
            )

        return registry

    def _load_bundle(self, component: str, bundle_path: Path) -> None:
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
            return

        self._bundles[(metadata.commodity, component)] = metadata

    def has(self, commodity: str, component: str) -> bool:
        return (commodity, component) in self._bundles

    def get(self, commodity: str, component: str) -> ArtifactMetadata | None:
        return self._bundles.get((commodity, component))

    @property
    def is_empty(self) -> bool:
        return not self._bundles

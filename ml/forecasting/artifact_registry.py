"""Cached registry of the committed forecasting artifact bundle.

Everything under ``<artifacts_dir>/`` is loaded once at API startup:

- ``{supply,price}/<commodity_slug>.joblib`` — fitted models; carry their own
  ``commodity`` key (Title Case).
- ``demand/{rice,vegetable_shared,banana}.joblib`` — cross-sectional FIES
  estimators keyed on ``artifact_name``, not ``commodity``. The
  commodity -> demand-artifact mapping (one shared VEG estimator backs both
  Tomato and Red Onion) comes from
  ``config/commodity_demand_registry.json``. When that config is absent the
  loader falls back to globbing ``demand/*.joblib`` and reading a ``commodity``
  key, which keeps synthetic-bundle tests working.
- ``prepared/*_features.csv`` + the two ``*_demand_pressure*`` tables — the
  actual observed/forecast series.
- ``config/*.json`` — demand registry, opportunity scoring, commodity flow.
- ``reports/*`` — deployment verdicts, model metrics, methodology. These are
  the verdict/metric source of truth for supply/price commodities whose
  joblib was not (or could not be) loaded.

`ArtifactRegistry.load` must work against a missing or empty directory: it
returns an empty registry rather than raising (unless ``strict=True``), so the
API can start and serve ``INSUFFICIENT_DATA`` for every component until real
artifacts land.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd

from ml.forecasting.domain import COMMODITIES, COMPONENTS

logger = logging.getLogger("agriwise.forecast")

Component = Literal["demand", "supply", "price"]

SCHEMA_VERSION = "3.2"

_CONFIG_DIR = "config"
_PREPARED_DIR = "prepared"
_REPORTS_DIR = "reports"
_DEMAND_REGISTRY_REL = Path(_CONFIG_DIR) / "commodity_demand_registry.json"

_CONFIG_FILES = {
    "opportunity_scoring": "opportunity_scoring_config.json",
    "commodity_flow": "commodity_flow_methodology.json",
}
_MODELED_COMPONENTS: tuple[str, ...] = ("supply", "price")
_DEMAND_PRESSURE_OBSERVED = "quarterly_demand_pressure_index.csv"
_DEMAND_PRESSURE_FORECAST = "future_demand_pressure_3q.csv"
_RED_ONION_PHYSICAL_DEMAND = "red_onion_demand_mt.csv"
_METHODOLOGY_REL = Path(_REPORTS_DIR) / "methodology_registry.json"
_REPORT_FILES = (
    "supply_deployment_verdicts",
    "price_deployment_verdicts",
    "supply_model_metrics",
    "price_model_metrics",
    "demand_validation_summary",
)


class ArtifactSchemaError(RuntimeError):
    """Raised by ``load(strict=True)`` when a bundle fails schema-3.2 checks."""


def slugify_commodity(commodity: str) -> str:
    return commodity.strip().lower().replace(" ", "_")


def _to_jsonable(obj):
    """Recursively coerce numpy scalars/arrays (as they arrive from joblib
    bundles) into plain Python so the values survive JSON serialization."""
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return [_to_jsonable(v) for v in obj.tolist()]
    return obj


@dataclass(frozen=True)
class ArtifactMetadata:
    """Verdict + provenance for one `(commodity, component)`.

    Sourced from the joblib bundle when one loaded, otherwise synthesized from
    ``reports/{component}_deployment_verdicts.csv``.
    """

    model_id: str
    commodity: str
    component: Component
    verdict: str
    metrics: dict = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    label: str | None = None
    selected_model: str | None = None
    reason: str | None = None
    schema_version: str | None = None
    target: str | None = None
    province_holdout: list[dict] = field(default_factory=list)


class ArtifactRegistry:
    """Cached lookup over the committed forecasting artifact bundle."""

    def __init__(self, artifacts_dir: Path) -> None:
        self._artifacts_dir = artifacts_dir
        self._bundles: dict[tuple[str, str], ArtifactMetadata] = {}
        self._model_bundles: dict[tuple[str, str], dict] = {}
        self._diagnostics: list[str] = []
        self._feature_tables: dict[tuple[str, str], pd.DataFrame] = {}
        self._demand_observed: pd.DataFrame = pd.DataFrame()
        self._demand_forecast: pd.DataFrame = pd.DataFrame()
        self._red_onion_physical_demand: pd.DataFrame = pd.DataFrame()
        self._configs: dict[str, dict] = {}
        self._reports: dict[str, pd.DataFrame] = {}
        self._methodology: dict = {}
        self._strict = False

    @classmethod
    def load(cls, artifacts_dir: Path, *, strict: bool = False) -> ArtifactRegistry:
        registry = cls(artifacts_dir)
        registry._strict = strict

        if not artifacts_dir.exists():
            logger.warning(
                "forecast artifacts directory missing at %s; registry loads empty "
                "and every component reports INSUFFICIENT_DATA",
                artifacts_dir,
            )
            return registry

        registry._load_reports()
        registry._load_prepared_tables()
        for key, filename in _CONFIG_FILES.items():
            registry._configs[key] = registry._read_json(
                artifacts_dir / _CONFIG_DIR / filename
            )
        registry._methodology = registry._read_json(artifacts_dir / _METHODOLOGY_REL)
        registry._validate_config_schema("opportunity_scoring")

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

        if registry.is_empty and not registry._reports:
            logger.warning(
                "forecast artifacts directory %s contained no loadable bundles; "
                "registry loads empty",
                artifacts_dir,
            )

        return registry

    # -- joblib bundles -----------------------------------------------------

    def _load_modeled_bundle(self, component: str, bundle_path: Path) -> None:
        """Load a supply/price bundle (or a legacy demand bundle carrying its
        own ``commodity`` key)."""
        try:
            bundle = joblib.load(bundle_path)
            commodity = str(bundle["commodity"])
            self._check_schema(bundle, bundle_path.name)
            metadata = ArtifactMetadata(
                model_id=str(bundle["model_id"]),
                commodity=commodity,
                component=component,  # type: ignore[arg-type]
                verdict=str(bundle["verdict"]),
                metrics=_to_jsonable(dict(bundle.get("metrics", {}))),
                limitations=list(bundle.get("limitations", [])),
                selected_model=bundle.get("strategy") or bundle.get("selected_model"),
                reason=bundle.get("reason") or bundle.get("verdict_reason"),
                schema_version=bundle.get("schema_version"),
                target=bundle.get("target"),
            )
        except ArtifactSchemaError:
            raise
        except Exception:
            logger.warning(
                "failed to load artifact bundle %s; skipping", bundle_path, exc_info=True
            )
            self._diagnostics.append(f"{component}: failed to load {bundle_path.name}")
            return

        self._bundles[(metadata.commodity, component)] = metadata
        self._model_bundles[(metadata.commodity, component)] = bundle

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
                self._diagnostics.append(
                    f"demand: unknown commodity slug {slug!r} in registry"
                )
                continue
            bundle_path = self._artifacts_dir / str(entry.get("artifact", ""))
            try:
                if bundle_path not in bundle_cache:
                    bundle_cache[bundle_path] = joblib.load(bundle_path)
                bundle = bundle_cache[bundle_path]
                self._check_schema(bundle, bundle_path.name)
                metrics = bundle.get("metrics") or bundle.get("weighted_metrics") or {}
                metadata = ArtifactMetadata(
                    model_id=str(bundle["model_id"]),
                    commodity=commodity,
                    component="demand",
                    verdict=str(bundle["verdict"]),
                    metrics=_to_jsonable(dict(metrics)),
                    limitations=list(bundle.get("limitations", [])),
                    label=entry.get("label"),
                    selected_model=bundle.get("selected_model"),
                    reason=bundle.get("verdict_reason") or bundle.get("reason"),
                    schema_version=bundle.get("schema_version"),
                    target=bundle.get("target") or entry.get("target"),
                    province_holdout=_to_jsonable(list(bundle.get("province_holdout", []))),
                )
            except ArtifactSchemaError:
                raise
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

    def _check_schema(self, bundle: dict, name: str) -> None:
        version = str(bundle.get("schema_version", ""))
        if version == SCHEMA_VERSION:
            return
        message = f"{name}: schema_version {version!r} != {SCHEMA_VERSION!r}"
        if self._strict:
            raise ArtifactSchemaError(message)
        self._diagnostics.append(message)

    def _validate_config_schema(self, key: str) -> None:
        config = self._configs.get(key) or {}
        if not config:
            return
        version = str(config.get("schema_version", ""))
        if version == SCHEMA_VERSION:
            return
        message = f"config/{key}: schema_version {version!r} != {SCHEMA_VERSION!r}"
        if self._strict:
            raise ArtifactSchemaError(message)
        self._diagnostics.append(message)

    # -- prepared tables / reports / config -------------------------------

    def _load_prepared_tables(self) -> None:
        prepared = self._artifacts_dir / _PREPARED_DIR
        if not prepared.is_dir():
            return

        for commodity in COMMODITIES:
            slug = slugify_commodity(commodity)
            for component in _MODELED_COMPONENTS:
                frame = self._read_csv(prepared / f"{slug}_{component}_features.csv")
                if frame is not None:
                    self._feature_tables[(commodity, component)] = frame

        observed = self._read_csv(prepared / _DEMAND_PRESSURE_OBSERVED)
        if observed is not None:
            self._demand_observed = observed
        forecast = self._read_csv(prepared / _DEMAND_PRESSURE_FORECAST)
        if forecast is not None:
            self._demand_forecast = forecast
        physical_demand = self._read_csv(prepared / _RED_ONION_PHYSICAL_DEMAND)
        if physical_demand is not None:
            self._red_onion_physical_demand = physical_demand

    def _load_reports(self) -> None:
        reports = self._artifacts_dir / _REPORTS_DIR
        if not reports.is_dir():
            return
        for name in _REPORT_FILES:
            frame = self._read_csv(reports / f"{name}.csv")
            if frame is not None:
                self._reports[name] = frame

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text())
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            logger.warning(
                "failed to read artifact config %s; ignoring", path, exc_info=True
            )
            self._diagnostics.append(f"config: failed to read {path.name}")
            return {}

    def _read_csv(self, path: Path) -> pd.DataFrame | None:
        if not path.is_file():
            return None
        try:
            parse_dates = ["date"] if "date" in _csv_header(path) else None
            return pd.read_csv(path, parse_dates=parse_dates)
        except (OSError, ValueError, pd.errors.ParserError):
            logger.warning(
                "failed to read prepared table %s; ignoring", path, exc_info=True
            )
            self._diagnostics.append(f"prepared: failed to read {path.name}")
            return None

    # -- lookups ----------------------------------------------------------

    def has(self, commodity: str, component: str) -> bool:
        return self.get(commodity, component) is not None

    def get(self, commodity: str, component: str) -> ArtifactMetadata | None:
        """Verdict + provenance for `(commodity, component)`.

        Prefers the loaded joblib metadata; falls back to a
        ``reports/{component}_deployment_verdicts.csv`` row so supply/price
        commodities whose model joblib is absent still report their verdict.
        """
        loaded = self._bundles.get((commodity, component))
        if loaded is not None:
            return loaded
        if component in _MODELED_COMPONENTS:
            return self._metadata_from_report(commodity, component)
        return None

    def _metadata_from_report(
        self, commodity: str, component: str
    ) -> ArtifactMetadata | None:
        frame = self._reports.get(f"{component}_deployment_verdicts")
        if frame is None:
            return None
        slug = slugify_commodity(commodity)
        rows = frame[frame["commodity"] == slug]
        if rows.empty:
            return None
        row = rows.iloc[0].to_dict()
        metric_keys = ("MAE", "RMSE", "R2", "MAPE", "sMAPE", "WAPE", "MASE", "Bias")
        metrics = {
            k: _to_jsonable(row[k])
            for k in metric_keys
            if k in row and pd.notna(row[k])
        }
        return ArtifactMetadata(
            model_id=f"{slug}-{component}",
            commodity=commodity,
            component=component,  # type: ignore[arg-type]
            verdict=str(row["verdict"]),
            metrics=metrics,
            selected_model=(row.get("selected_model") or None)
            if pd.notna(row.get("selected_model"))
            else None,
            reason=(row.get("reason") or None) if pd.notna(row.get("reason")) else None,
            schema_version=SCHEMA_VERSION,
        )

    def model_bundle(self, commodity: str, component: str) -> dict | None:
        """The raw joblib dict (``model``/``features``/``strategy``/
        ``seasonal_period``/``history_tail``) when one loaded, else None."""
        return self._model_bundles.get((commodity, component))

    def feature_table(self, commodity: str, component: str) -> pd.DataFrame | None:
        """The `prepared/{commodity}_{component}_features.csv` frame, or None."""
        frame = self._feature_tables.get((commodity, component))
        return frame.copy() if frame is not None else None

    def report(self, name: str) -> pd.DataFrame | None:
        """A cached `reports/<name>.csv` frame, or None."""
        frame = self._reports.get(name)
        return frame.copy() if frame is not None else None

    @property
    def demand_pressure_observed(self) -> pd.DataFrame:
        """`prepared/quarterly_demand_pressure_index.csv` (empty frame if absent)."""
        return self._demand_observed.copy()

    @property
    def demand_pressure_forecast(self) -> pd.DataFrame:
        """`prepared/future_demand_pressure_3q.csv` (empty frame if absent)."""
        return self._demand_forecast.copy()

    @property
    def red_onion_physical_demand(self) -> pd.DataFrame:
        """PSA SUA/HFCE/Denton Red Onion quarterly demand, when deployed."""
        return self._red_onion_physical_demand.copy()

    @property
    def opportunity_config(self) -> dict:
        """`config/opportunity_scoring_config.json` ({} if absent)."""
        return self._configs.get("opportunity_scoring", {})

    @property
    def commodity_flow_methodology(self) -> dict:
        """`config/commodity_flow_methodology.json` ({} if absent)."""
        return self._configs.get("commodity_flow", {})

    @property
    def methodology(self) -> dict:
        """`reports/methodology_registry.json` ({} if absent)."""
        return dict(self._methodology)

    @property
    def is_empty(self) -> bool:
        return not self._bundles

    @property
    def diagnostics(self) -> list[str]:
        """Human-readable notes about artifacts that were expected but skipped."""
        return list(self._diagnostics)


def _csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        return handle.readline().strip().split(",")

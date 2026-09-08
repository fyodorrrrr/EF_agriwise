from __future__ import annotations

import json
from pathlib import Path

import joblib
import pytest

from ml.forecasting.artifact_registry import ArtifactRegistry, slugify_commodity


def _write_demand_bundle(path: Path, *, model_id: str, verdict: str) -> None:
    """A demand bundle as the replaced ml/artifacts ships them: keyed on
    ``artifact_name``, not ``commodity``, and metrics under ``weighted_metrics``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "schema_version": "3.2",
            "kind": "demand_proxy_estimator",
            "artifact_name": path.stem,
            "model_id": model_id,
            "verdict": verdict,
            "verdict_reason": "test",
            "weighted_metrics": {"r2": 0.31},
            "limitations": ["FIES expenditure-category proxy."],
        },
        path,
    )

# apps/api/tests/test_artifact_registry.py -> parents[3] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMITTED_ARTIFACTS_DIR = _REPO_ROOT / "ml" / "artifacts"

# Every (commodity, component) the registry must resolve a verdict for against
# the committed bundle — from a joblib, or from a reports/ deployment-verdicts
# row when the model joblib is absent. Red Onion price has a row too, with
# verdict INSUFFICIENT_DATA.
_EXPECTED_RESOLVED = [
    (commodity, component)
    for commodity in ("Rice", "Tomato", "Red Onion", "Banana")
    for component in ("demand", "supply", "price")
]


def test_load_missing_directory_returns_empty_registry_without_raising(tmp_path):
    registry = ArtifactRegistry.load(tmp_path / "does_not_exist")

    assert registry.is_empty
    assert registry.get("Rice", "demand") is None
    assert registry.has("Rice", "demand") is False


def test_load_empty_directory_returns_empty_registry(tmp_path):
    (tmp_path / "demand").mkdir()

    registry = ArtifactRegistry.load(tmp_path)

    assert registry.is_empty


def test_load_reads_a_well_formed_bundle(tmp_path):
    demand_dir = tmp_path / "demand"
    demand_dir.mkdir()
    joblib.dump(
        {
            "commodity": "Rice",
            "model_id": "rice-demand-v1",
            "verdict": "USABLE_PROXY",
            "metrics": {"mae": 1.2},
            "limitations": ["proxy only"],
        },
        demand_dir / f"{slugify_commodity('Rice')}.joblib",
    )

    registry = ArtifactRegistry.load(tmp_path)

    meta = registry.get("Rice", "demand")
    assert meta is not None
    assert meta.model_id == "rice-demand-v1"
    assert meta.verdict == "USABLE_PROXY"
    assert meta.metrics == {"mae": 1.2}


def test_load_skips_corrupt_bundle_without_raising(tmp_path):
    demand_dir = tmp_path / "demand"
    demand_dir.mkdir()
    (demand_dir / "rice.joblib").write_bytes(b"not a joblib file")

    registry = ArtifactRegistry.load(tmp_path)

    assert registry.is_empty


def test_demand_bundles_resolve_through_the_demand_registry_config(tmp_path):
    _write_demand_bundle(
        tmp_path / "demand" / "rice.joblib", model_id="rice-demand-v1", verdict="USABLE_PROXY"
    )
    _write_demand_bundle(
        tmp_path / "demand" / "vegetable_shared.joblib",
        model_id="vegetable_shared-demand-v1",
        verdict="INDICATIVE_PROXY",
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "commodity_demand_registry.json").write_text(
        json.dumps(
            {
                "rice": {
                    "artifact": "demand/rice.joblib",
                    "label": "Cereal Household Demand Proxy",
                },
                "tomato": {
                    "artifact": "demand/vegetable_shared.joblib",
                    "label": "Vegetable Household Demand Proxy",
                },
                "red_onion": {
                    "artifact": "demand/vegetable_shared.joblib",
                    "label": "Vegetable Household Demand Proxy",
                },
            }
        )
    )

    registry = ArtifactRegistry.load(tmp_path)

    rice = registry.get("Rice", "demand")
    tomato = registry.get("Tomato", "demand")
    red_onion = registry.get("Red Onion", "demand")

    assert rice is not None and rice.verdict == "USABLE_PROXY"
    assert rice.metrics == {"r2": 0.31}  # falls back to weighted_metrics
    assert rice.label == "Cereal Household Demand Proxy"
    # Tomato and Red Onion are backed by the one shared VEG estimator.
    assert tomato is not None and red_onion is not None
    assert tomato.model_id == red_onion.model_id == "vegetable_shared-demand-v1"


def _write_csv(path: Path, header: str, *rows: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n")


def test_load_reads_prepared_tables_demand_pressure_and_configs(tmp_path):
    _write_csv(
        tmp_path / "prepared" / "rice_supply_features.csv",
        "geolocation,date,target,lag_4",
        "Laguna,2026-01-01,100.0,90.0",
        "Laguna,2026-04-01,,95.0",
    )
    _write_csv(
        tmp_path / "prepared" / "quarterly_demand_pressure_index.csv",
        "commodity,province,date,demand_pressure_index",
        "rice,Laguna,2025-10-01,101.2",
    )
    _write_csv(
        tmp_path / "prepared" / "future_demand_pressure_3q.csv",
        "commodity,province,date,estimated_demand_pressure_index,confidence",
        "rice,Laguna,2026-01-01,103.4,moderate_proxy",
    )
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "opportunity_scoring_config.json").write_text(
        json.dumps(
            {
                "schema_version": "3.2",
                "components": {"demand_pressure_index": {"weight": 0.35}},
            }
        )
    )

    registry = ArtifactRegistry.load(tmp_path)

    supply = registry.feature_table("Rice", "supply")
    assert supply is not None
    assert list(supply.columns) == ["geolocation", "date", "target", "lag_4"]
    assert supply["target"].isna().sum() == 1  # the future row

    assert registry.feature_table("Banana", "price") is None  # not provided

    assert len(registry.demand_pressure_observed) == 1
    assert registry.demand_pressure_forecast.iloc[0]["confidence"] == "moderate_proxy"

    assert registry.opportunity_config["components"]["demand_pressure_index"]["weight"] == 0.35


@pytest.mark.skipif(
    not _COMMITTED_ARTIFACTS_DIR.is_dir(),
    reason="committed artifact bundle not present in this checkout",
)
def test_committed_bundle_resolves_every_commodity_component():
    """Every commodity/component resolves a verdict against the real bundle,
    and nothing was silently skipped."""
    registry = ArtifactRegistry.load(_COMMITTED_ARTIFACTS_DIR)

    missing = [
        pair for pair in _EXPECTED_RESOLVED if not registry.has(*pair)
    ]
    assert not missing, f"unresolved: {missing}"
    assert registry.diagnostics == [], registry.diagnostics

    # Demand: shared VEG estimator backs Tomato + Red Onion.
    assert (
        registry.get("Tomato", "demand").model_id
        == registry.get("Red Onion", "demand").model_id
    )
    # The price/rice joblib carries a fitted model; the red_onion supply joblib
    # is present but model-free (seasonal-naive / INSUFFICIENT_DATA).
    assert registry.model_bundle("Rice", "price")["model"] is not None
    ro_supply = registry.model_bundle("Red Onion", "supply")
    assert ro_supply is not None and ro_supply["model"] is None

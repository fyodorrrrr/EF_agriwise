from __future__ import annotations

from pathlib import Path

import joblib
import pytest

from ml.forecasting.artifact_registry import ArtifactRegistry, slugify_commodity

# apps/api/tests/test_artifact_registry.py -> parents[3] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMITTED_ARTIFACTS_DIR = _REPO_ROOT / "ml" / "artifacts"

# The bundles committed under ml/artifacts/. Supply covers all four commodities;
# price has no red_onion artifact (no deployable price model).
_EXPECTED_BUNDLES = [
    ("Rice", "demand"),
    ("Tomato", "demand"),
    ("Red Onion", "demand"),
    ("Banana", "demand"),
    ("Rice", "supply"),
    ("Tomato", "supply"),
    ("Red Onion", "supply"),
    ("Banana", "supply"),
    ("Rice", "price"),
    ("Tomato", "price"),
    ("Banana", "price"),
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


@pytest.mark.skipif(
    not _COMMITTED_ARTIFACTS_DIR.is_dir(),
    reason="committed artifact bundles not present in this checkout",
)
def test_all_committed_artifact_bundles_load():
    """Every bundle under ml/artifacts/ must register.

    Regression guard: the shared VEG demand bundle (Tomato, Red Onion) pickles
    an XGBoost estimator, so a runtime without `xgboost` installed silently
    drops those two commodities' demand to INSUFFICIENT_DATA.
    """
    registry = ArtifactRegistry.load(_COMMITTED_ARTIFACTS_DIR)

    missing = [
        (commodity, component)
        for commodity, component in _EXPECTED_BUNDLES
        if not registry.has(commodity, component)
    ]

    assert not missing, f"artifact bundles failed to load: {missing}"

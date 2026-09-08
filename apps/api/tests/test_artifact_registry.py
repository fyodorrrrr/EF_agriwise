from __future__ import annotations

import joblib

from ml.forecasting.artifact_registry import ArtifactRegistry, slugify_commodity


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

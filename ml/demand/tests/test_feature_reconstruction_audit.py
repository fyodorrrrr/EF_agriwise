from pathlib import Path

import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
EVAL = REPO_ROOT / "data" / "processed" / "demand" / "evaluation"


def test_reconstruction_audit_is_complete_and_fail_closed():
    manifest = pd.read_json(PACKAGE_ROOT / "artifacts" / "xgboost_model_features.json").iloc[:, 0]
    validation = pd.read_csv(EVAL / "feature_reconstruction_validation.csv")
    assert len(manifest) == 129
    assert len(validation) == 129
    assert validation.feature_name.tolist() == manifest.tolist()
    assert validation.matched_households.eq(0).all()
    assert validation.exact_match_rate.isna().all()


def test_empty_contract_does_not_claim_unvalidated_features():
    contract = pd.read_csv(EVAL / "validated_quarterly_feature_contract.csv")
    assert contract.empty


def test_reconstruction_audit_has_no_target_feature():
    validation = pd.read_csv(EVAL / "feature_reconstruction_validation.csv")
    assert not validation.feature_name.str.upper().eq("BREAD").any()

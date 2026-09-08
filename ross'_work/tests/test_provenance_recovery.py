from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evaluation"


def test_historical_2023_regeneration_matches_every_column():
    comparison = pd.read_csv(EVAL / "training_table_regeneration_comparison.csv")
    assert len(comparison) == 136
    assert comparison.present_in_recovered.all()
    assert comparison.exact_match_rate.eq(1.0).all()


def test_household_id_provenance_is_seq_no_and_validated():
    link = pd.read_csv(EVAL / "household_link_validation.csv")
    assert len(link) == 8156
    assert link.household_id_equals_seq_no.all()
    assert link.member_count_matches.all()
    assert link.province_matches.all()
    assert link.weight_matches.all()


def test_all_model_features_have_recovered_code_provenance():
    provenance = pd.read_csv(EVAL / "feature_engineering_provenance.csv")
    assert len(provenance) == 129
    assert provenance.formula_provenance.eq("VERIFIED_FROM_CODE").all()

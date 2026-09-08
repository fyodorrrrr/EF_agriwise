"""Materialize vegetable-target training tables from bread-preprocessed features."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .train_vegetable_101 import RAW_2018, RAW_2023, TRAIN_2018, TRAIN_2023, attach_vegetable_target

DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "processed" / "demand"
OUTPUT_ROOT = DATA_ROOT / "fies_lfs" / "vegetable"


def _prepare(source: Path, raw_summary: Path, raw_household_id: str) -> pd.DataFrame:
    bread_preprocessed = pd.read_csv(source, low_memory=False)
    vegetable = attach_vegetable_target(bread_preprocessed, raw_summary, raw_household_id)
    expected_columns = [column for column in bread_preprocessed if column != "BREAD"] + ["VEG"]
    if vegetable.columns.tolist() != expected_columns:
        raise RuntimeError("Vegetable table does not preserve the bread preprocessing schema")
    if len(vegetable) != len(bread_preprocessed):
        raise RuntimeError("Vegetable target join changed the training row count")
    return vegetable


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    train_2018 = _prepare(TRAIN_2018, RAW_2018, "SEQUENCE_NO")
    train_2023 = _prepare(TRAIN_2023, RAW_2023, "SEQ_NO")
    combined = pd.concat([train_2018, train_2023], ignore_index=True)

    train_2018.to_csv(OUTPUT_ROOT / "fies_lfs_2018_vegetable_training_table.csv", index=False)
    train_2023.to_csv(OUTPUT_ROOT / "fies_lfs_2023_vegetable_training_table.csv", index=False)
    combined.to_csv(OUTPUT_ROOT / "fies_lfs_2018_2023_vegetable_training_table.csv", index=False)


if __name__ == "__main__":
    main()

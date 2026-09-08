"""Proportional first-difference Denton temporal benchmarking."""

from __future__ import annotations

import numpy as np


def proportional_denton(indicator: np.ndarray, annual_totals: np.ndarray) -> np.ndarray:
    """Benchmark quarterly values to annual totals using changes in value/indicator.

    The constrained least-squares problem is solved directly with its KKT system.
    ``indicator`` is chronological and contains exactly four quarters per annual total.
    """
    indicator = np.asarray(indicator, dtype=float)
    annual_totals = np.asarray(annual_totals, dtype=float)
    n = len(indicator)
    if n != 4 * len(annual_totals) or np.any(indicator <= 0):
        raise ValueError("Indicator must be positive and have four observations per annual total")
    difference = np.diff(np.eye(n), axis=0)
    ratio_difference = difference @ np.diag(1.0 / indicator)
    hessian = ratio_difference.T @ ratio_difference
    constraints = np.zeros((len(annual_totals), n))
    for i in range(len(annual_totals)):
        constraints[i, i * 4 : (i + 1) * 4] = 1.0
    kkt = np.block(
        [[hessian, constraints.T], [constraints, np.zeros((len(annual_totals), len(annual_totals)))]]
    )
    solution = np.linalg.lstsq(kkt, np.r_[np.zeros(n), annual_totals], rcond=None)[0][:n]
    # Eliminate floating-point reconciliation residue exactly within each annual block.
    for i, total in enumerate(annual_totals):
        block = slice(i * 4, (i + 1) * 4)
        solution[block.stop - 1] += total - solution[block].sum()
    return solution

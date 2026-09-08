"""Small rolling-origin forecasting helpers for the annual PCC series."""

from __future__ import annotations

import numpy as np


METHODS = ("naive", "ma3", "ma5", "linear_trend", "recent_linear_trend", "holt")


def _holt_parameters(values: np.ndarray) -> tuple[float, float]:
    """Choose a small fixed grid by one-step in-sample SSE."""
    best = (float("inf"), 0.4, 0.2)
    for alpha in (0.2, 0.4, 0.6, 0.8):
        for beta in (0.1, 0.3, 0.5):
            level, trend, sse = values[0], values[1] - values[0], 0.0
            for actual in values[1:]:
                prediction = level + trend
                sse += (actual - prediction) ** 2
                previous_level = level
                level = alpha * actual + (1 - alpha) * (level + trend)
                trend = beta * (level - previous_level) + (1 - beta) * trend
            best = min(best, (sse, alpha, beta))
    return best[1], best[2]


def _holt_forecast(values: np.ndarray, horizon: int) -> float:
    alpha, beta = _holt_parameters(values)
    level, trend = values[0], values[1] - values[0]
    for actual in values[1:]:
        previous_level = level
        level = alpha * actual + (1 - alpha) * (level + trend)
        trend = beta * (level - previous_level) + (1 - beta) * trend
    return float(level + horizon * trend)


def forecast(values: np.ndarray, method: str, horizon: int = 1) -> float:
    """Forecast one point from a chronological, non-empty series."""
    if method == "naive":
        return float(values[-1])
    if method == "ma3":
        return float(values[-min(3, len(values)) :].mean())
    if method == "ma5":
        return float(values[-min(5, len(values)) :].mean())
    if method in {"linear_trend", "recent_linear_trend"}:
        window = len(values) if method == "linear_trend" else min(8, len(values))
        x = np.arange(window)
        slope, intercept = np.polyfit(x, values[-window:], 1)
        return float(intercept + slope * (window - 1 + horizon))
    if method == "holt":
        return _holt_forecast(values, horizon)
    raise ValueError(f"Unknown method: {method}")


def evaluate(values: np.ndarray, methods: tuple[str, ...] = METHODS, holdouts: int = 8):
    """One-step rolling-origin evaluation; returns metrics for each method."""
    start = max(5, len(values) - holdouts)
    rows = []
    for method in methods:
        errors, actuals = [], []
        for origin in range(start, len(values)):
            prediction = forecast(values[:origin], method)
            errors.append(prediction - values[origin])
            actuals.append(values[origin])
        errors, actuals = np.asarray(errors), np.asarray(actuals)
        rows.append(
            {
                "method": method,
                "mae": float(np.mean(np.abs(errors))),
                "rmse": float(np.sqrt(np.mean(errors**2))),
                "mape": float(np.mean(np.abs(errors / actuals)) * 100),
                "bias": float(np.mean(errors)),
                "n_test": len(errors),
            }
        )
    best = min(rows, key=lambda row: (row["mae"], row["rmse"]))["method"]
    return rows, best

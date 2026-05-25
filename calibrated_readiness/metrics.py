"""Calibration metrics and the reliability table that backs the diagram.

The reliability table is the falsification artifact: for each probability bin we
report the mean predicted probability, the observed pass rate, and a Wilson
score interval on that observed rate. If predictions are honest, the diagonal
(predicted == observed) should fall inside the Wilson band for most bins.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm


@dataclass(frozen=True)
class Bin:
    lo: float
    hi: float
    count: int
    mean_predicted: float
    observed_rate: float
    wilson_lo: float
    wilson_hi: float


def wilson_interval(successes: int, n: int, ci_level: float) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Preferred over the normal approximation because it behaves sensibly for the
    small per-bin counts and near-0/near-1 rates that show up in reliability
    diagrams.
    """
    if n == 0:
        return (0.0, 1.0)
    z = norm.ppf(0.5 + ci_level / 2.0)
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def reliability_table(
    predicted: np.ndarray, outcome: np.ndarray, n_bins: int, ci_level: float
) -> list[Bin]:
    """Bin predictions into equal-width bins and summarise each bin."""
    assert predicted.shape == outcome.shape
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[Bin] = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        in_bin = (predicted >= lo) & (predicted < hi if i < n_bins - 1 else predicted <= hi)
        count = int(in_bin.sum())
        if count == 0:
            bins.append(Bin(lo, hi, 0, (lo + hi) / 2, float("nan"), float("nan"), float("nan")))
            continue
        successes = int(outcome[in_bin].sum())
        observed = successes / count
        w_lo, w_hi = wilson_interval(successes, count, ci_level)
        bins.append(
            Bin(lo, hi, count, float(predicted[in_bin].mean()), observed, w_lo, w_hi)
        )
    return bins


def expected_calibration_error(
    predicted: np.ndarray, outcome: np.ndarray, n_bins: int
) -> float:
    """ECE: sample-weighted mean gap between predicted prob and observed rate."""
    table = reliability_table(predicted, outcome, n_bins, ci_level=0.95)
    n = len(predicted)
    return float(
        sum(
            b.count / n * abs(b.mean_predicted - b.observed_rate)
            for b in table
            if b.count > 0
        )
    )


def max_calibration_error(
    predicted: np.ndarray, outcome: np.ndarray, n_bins: int
) -> float:
    """MCE: worst-case bin gap (the bin a manager should least trust)."""
    table = reliability_table(predicted, outcome, n_bins, ci_level=0.95)
    gaps = [abs(b.mean_predicted - b.observed_rate) for b in table if b.count > 0]
    return float(max(gaps)) if gaps else 0.0


def brier_score(predicted: np.ndarray, outcome: np.ndarray) -> float:
    """Mean squared error of probabilistic predictions (lower is better)."""
    return float(np.mean((predicted - outcome) ** 2))

"""Tests that lock the falsifiable claims of the calibration core.

Run with: pytest -q
These do not touch Azure or the network - they are the project's safety net.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibrated_readiness.calibration import fit_calibrator, readiness_with_ci
from calibrated_readiness.config import DEFAULT_CALIBRATION, DEFAULT_SIM
from calibrated_readiness.metrics import expected_calibration_error, wilson_interval
from calibrated_readiness.pipeline import run_benchmark


def test_calibration_reduces_ece():
    """The headline claim: temperature scaling lowers held-out ECE."""
    result, *_ = run_benchmark(DEFAULT_SIM, DEFAULT_CALIBRATION, "temperature")
    assert result.cal_ece < result.raw_ece
    assert result.ece_reduction_pct > 30  # comfortably above noise on this benchmark


def test_temperature_above_one_when_overconfident():
    """A gain>1 simulator is overconfident, so the fitted temperature must be >1."""
    result, *_ = run_benchmark(DEFAULT_SIM, DEFAULT_CALIBRATION, "temperature")
    assert result.temperature is not None and result.temperature > 1.0


def test_perfectly_calibrated_input_stays_calibrated():
    """If the raw score already equals P(pass), calibration shouldn't wreck it."""
    rng = np.random.default_rng(0)
    p = rng.uniform(0.05, 0.95, size=4000)
    y = rng.binomial(1, p)
    cal = fit_calibrator(p, y, "temperature")
    assert abs(cal.temperature - 1.0) < 0.25
    assert expected_calibration_error(cal.predict(p), y, 10) < 0.05


def test_wilson_interval_brackets_rate():
    lo, hi = wilson_interval(successes=8, n=10, ci_level=0.95)
    assert 0.0 <= lo < 0.8 < hi <= 1.0


def test_readiness_ci_is_ordered_and_bounded():
    result, cohort, _, test_idx = run_benchmark(
        DEFAULT_SIM, DEFAULT_CALIBRATION, "temperature"
    )
    train_mask = np.ones(len(cohort), dtype=bool)
    train_mask[test_idx] = False
    estimates = readiness_with_ci(
        raw_train=cohort.raw_score[train_mask],
        outcome_train=cohort.outcome[train_mask],
        raw_target=cohort.raw_score[test_idx][:20],
        target_ids=cohort.learner_id[test_idx][:20],
        method="temperature",
        threshold=DEFAULT_CALIBRATION.readiness_threshold,
        bootstrap_rounds=50,
        ci_level=0.95,
        seed=1,
    )
    for e in estimates:
        assert 0.0 <= e.ci_lo <= e.calibrated_prob <= e.ci_hi <= 1.0

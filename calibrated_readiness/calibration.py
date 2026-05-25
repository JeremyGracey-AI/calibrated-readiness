"""Phase 3 - the calibration core (the project's differentiator).

Turns a raw, overconfident readiness score into an honest probability of
passing, and attaches a confidence interval so readiness is a *measured
quantity*, not a vibe.

Two calibration methods:
  - "temperature": 1-parameter logit scaling. Minimal, interpretable, and the
    right inductive bias when miscalibration is a slope/over-confidence issue.
  - "isotonic":    non-parametric monotone fit. More flexible, no shape
    assumption, but needs more data and can overfit small cohorts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression

Method = Literal["temperature", "isotonic"]
_EPS = 1e-6


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, _EPS, 1.0 - _EPS)
    return np.log(p / (1.0 - p))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _log_loss(prob: np.ndarray, outcome: np.ndarray) -> float:
    prob = np.clip(prob, _EPS, 1.0 - _EPS)
    return float(-np.mean(outcome * np.log(prob) + (1 - outcome) * np.log(1 - prob)))


def _fit_temperature(raw: np.ndarray, outcome: np.ndarray) -> float:
    """Find the temperature T>0 that minimises log loss of sigma(logit(raw)/T)."""
    logits = _logit(raw)

    def objective(t: float) -> float:
        return _log_loss(_sigmoid(logits / t), outcome)

    result = minimize_scalar(objective, bounds=(0.05, 20.0), method="bounded")
    return float(result.x)


@dataclass
class Calibrator:
    """A fitted calibration map from raw score -> calibrated probability."""

    method: Method
    temperature: float | None = None
    _isotonic: IsotonicRegression | None = None

    def predict(self, raw: np.ndarray) -> np.ndarray:
        if self.method == "temperature":
            assert self.temperature is not None
            return _sigmoid(_logit(raw) / self.temperature)
        if self.method == "isotonic":
            assert self._isotonic is not None
            return self._isotonic.predict(raw)
        raise ValueError(f"unknown method: {self.method}")


def fit_calibrator(raw: np.ndarray, outcome: np.ndarray, method: Method) -> Calibrator:
    assert raw.shape == outcome.shape, "raw scores and outcomes must align"
    if method == "temperature":
        return Calibrator(method=method, temperature=_fit_temperature(raw, outcome))
    if method == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(raw, outcome)
        return Calibrator(method=method, _isotonic=iso)
    raise ValueError(f"unknown method: {method}")


@dataclass(frozen=True)
class ReadinessEstimate:
    """Readiness for one learner as a measured quantity with an interval."""

    learner_id: str
    raw_score: float
    calibrated_prob: float
    ci_lo: float
    ci_hi: float
    is_ready: bool  # lower CI bound clears the threshold -> defensibly ready


def readiness_with_ci(
    raw_train: np.ndarray,
    outcome_train: np.ndarray,
    raw_target: np.ndarray,
    target_ids: np.ndarray,
    method: Method,
    threshold: float,
    bootstrap_rounds: int,
    ci_level: float,
    seed: int,
) -> list[ReadinessEstimate]:
    """Bootstrap the calibration fit to put a confidence interval on each
    learner's calibrated readiness.

    The point estimate uses the full-data fit; the interval comes from refitting
    on resampled training data, which propagates the *calibration* uncertainty
    (how well we know the map) into the per-learner number.
    """
    point = fit_calibrator(raw_train, outcome_train, method).predict(raw_target)

    rng = np.random.default_rng(seed)
    n_train = len(raw_train)
    draws = np.empty((bootstrap_rounds, len(raw_target)))
    for b in range(bootstrap_rounds):
        idx = rng.integers(0, n_train, size=n_train)
        cal = fit_calibrator(raw_train[idx], outcome_train[idx], method)
        draws[b] = cal.predict(raw_target)

    alpha = (1.0 - ci_level) / 2.0
    lo = np.quantile(draws, alpha, axis=0)
    hi = np.quantile(draws, 1.0 - alpha, axis=0)

    return [
        ReadinessEstimate(
            learner_id=str(target_ids[i]),
            raw_score=float(raw_target[i]),
            calibrated_prob=float(point[i]),
            ci_lo=float(lo[i]),
            ci_hi=float(hi[i]),
            is_ready=bool(lo[i] >= threshold),
        )
        for i in range(len(raw_target))
    ]

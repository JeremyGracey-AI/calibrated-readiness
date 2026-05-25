"""Central, reproducible configuration for the Calibrated Readiness benchmark.

Every number that affects a published figure lives here so the headline claims
("ECE cut by ~N% on our synthetic benchmark") are traceable to two knobs the
README is explicit about: the simulator ``gain`` and the bin count.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimConfig:
    """Parameters of the latent-ability generative process (Phase 1).

    The model is a 2-parameter IRT-style process. ``gain`` is the single knob
    that controls how *overconfident* the system's raw readiness score is, and
    therefore how much miscalibration the calibration layer has to remove.
    """

    n_learners: int = 600
    discrimination: float = 1.7  # IRT "a": how sharply pass-prob rises with ability
    difficulty: float = 0.0  # IRT "b": ability at which true pass-prob is 0.5
    practice_noise: float = 0.55  # std of the system's noisy ability estimate
    gain: float = 1.9  # >1 => raw score is overconfident (the thing we fix)
    seed: int = 7

    def __post_init__(self) -> None:
        assert self.n_learners >= 100, "need a meaningful cohort to bin reliably"
        assert self.gain > 0, "gain must be positive"
        assert self.practice_noise > 0, "noise must be positive"


@dataclass(frozen=True)
class CalibrationConfig:
    """Parameters of the calibration + evaluation layer (Phase 3)."""

    test_fraction: float = 0.5  # held-out split the headline ECE is reported on
    n_bins: int = 10  # reliability bins (the second documented knob)
    bootstrap_rounds: int = 300  # resamples for per-learner readiness CIs
    ci_level: float = 0.95
    readiness_threshold: float = 0.80  # calibrated P(pass) needed to be "ready"
    seed: int = 7

    def __post_init__(self) -> None:
        assert 0.1 <= self.test_fraction <= 0.9, "keep both splits usable"
        assert self.n_bins >= 5, "too few bins hides miscalibration"
        assert 0.5 < self.ci_level < 1.0, "ci_level is a probability"


DEFAULT_SIM = SimConfig()
DEFAULT_CALIBRATION = CalibrationConfig()

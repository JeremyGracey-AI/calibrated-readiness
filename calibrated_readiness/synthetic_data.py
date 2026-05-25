"""Phase 1 - synthetic learners from a latent-ability generative process.

Two-tier ground truth, which is what makes the readiness claim *falsifiable*:

  Tier 1 (latent truth)   p_true = sigma(a * (theta - b))
                          the learner's real probability of passing.
  Tier 2 (observed label) y ~ Bernoulli(p_true)
                          the realized exam outcome we calibrate against.

The system never sees ``theta`` or ``p_true``. It only sees a noisy practice
signal and emits a *raw* readiness score that is deliberately overconfident
(controlled by ``gain``). Calibration's job is to turn that raw score into an
honest probability that matches the Tier-2 outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import SimConfig


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


@dataclass(frozen=True)
class Cohort:
    """A generated cohort. All arrays are aligned by learner index."""

    learner_id: np.ndarray  # str ids, shape (n,)
    ability: np.ndarray  # latent theta, shape (n,) - HIDDEN from the system
    true_pass_prob: np.ndarray  # Tier-1 truth, shape (n,) - HIDDEN
    outcome: np.ndarray  # Tier-2 observed pass/fail in {0,1}, shape (n,)
    raw_score: np.ndarray  # system's overconfident readiness score in (0,1)

    def __len__(self) -> int:
        return len(self.learner_id)


def generate_cohort(config: SimConfig) -> Cohort:
    """Generate a reproducible cohort under the IRT-style process."""
    rng = np.random.default_rng(config.seed)
    n = config.n_learners
    a, b = config.discrimination, config.difficulty

    ability = rng.normal(0.0, 1.0, size=n)
    true_pass_prob = _sigmoid(a * (ability - b))
    outcome = rng.binomial(1, true_pass_prob).astype(int)

    # The system estimates ability from noisy practice data, then turns it into
    # a probability with an inflated slope (gain > 1) -> systematic overconfidence.
    observed_ability = ability + rng.normal(0.0, config.practice_noise, size=n)
    raw_logit = config.gain * a * (observed_ability - b)
    raw_score = _sigmoid(raw_logit)

    learner_id = np.array([f"L{i:04d}" for i in range(n)])
    return Cohort(
        learner_id=learner_id,
        ability=ability,
        true_pass_prob=true_pass_prob,
        outcome=outcome,
        raw_score=raw_score,
    )


def train_test_split(
    cohort: Cohort, test_fraction: float, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Return (train_index, test_index). The calibrator is fit on train only;
    the headline ECE is reported on test only - no peeking."""
    assert 0.0 < test_fraction < 1.0
    rng = np.random.default_rng(seed)
    n = len(cohort)
    perm = rng.permutation(n)
    n_test = int(round(n * test_fraction))
    return perm[n_test:], perm[:n_test]

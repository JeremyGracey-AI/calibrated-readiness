"""Function tools the agents call.

These are plain, typed Python functions - the Microsoft Agent Framework infers
the tool schema from the signature and docstring. Crucially, `assess_readiness`
and `cohort_risk_summary` read from the SAME calibration pipeline the 60-second
verification uses, so an agent can never quote a readiness number that the
reliability diagram hasn't already justified.

The Work IQ / Fabric IQ tools are clearly-labeled patterns over synthetic data:
they show *where* those Microsoft signals would plug in, without pretending to
call live tenants in this hackathon build.
"""

from __future__ import annotations

import functools

import numpy as np

from .calibration import readiness_with_ci
from .config import DEFAULT_CALIBRATION, DEFAULT_SIM
from .pipeline import run_benchmark


@functools.lru_cache(maxsize=1)
def _state():
    """Fit the calibrator once and cache it. Returns (cohort, train_mask, test_idx)."""
    _, cohort, _, test_idx = run_benchmark(DEFAULT_SIM, DEFAULT_CALIBRATION, "temperature")
    train_mask = np.ones(len(cohort), dtype=bool)
    train_mask[test_idx] = False
    return cohort, train_mask, test_idx


def _estimate(learner_ids: list[str]):
    cohort, train_mask, _ = _state()
    id_to_row = {str(lid): i for i, lid in enumerate(cohort.learner_id)}
    rows = [id_to_row[lid] for lid in learner_ids]
    return readiness_with_ci(
        raw_train=cohort.raw_score[train_mask],
        outcome_train=cohort.outcome[train_mask],
        raw_target=cohort.raw_score[rows],
        target_ids=cohort.learner_id[rows],
        method="temperature",
        threshold=DEFAULT_CALIBRATION.readiness_threshold,
        bootstrap_rounds=200,
        ci_level=DEFAULT_CALIBRATION.ci_level,
        seed=DEFAULT_CALIBRATION.seed,
    )


def assess_readiness(learner_id: str) -> dict:
    """Return the calibrated probability that a learner passes the certification,
    with a 95% confidence interval and a defensible ready/not-ready decision.

    Args:
        learner_id: the learner identifier, e.g. "L0042".
    """
    cohort, _, _ = _state()
    if learner_id not in set(map(str, cohort.learner_id)):
        return {"error": f"unknown learner_id '{learner_id}'"}
    e = _estimate([learner_id])[0]
    band = (
        "ready" if e.is_ready
        else "borderline" if e.calibrated_prob >= DEFAULT_CALIBRATION.readiness_threshold
        else "at_risk"
    )
    return {
        "learner_id": e.learner_id,
        "calibrated_pass_probability": round(e.calibrated_prob, 3),
        "ci95": [round(e.ci_lo, 3), round(e.ci_hi, 3)],
        "raw_score": round(e.raw_score, 3),
        "threshold": DEFAULT_CALIBRATION.readiness_threshold,
        "decision": band,
        "rationale": (
            "Ready only if the LOWER confidence bound clears the threshold, so the "
            "call survives calibration uncertainty - not just a point estimate."
        ),
    }


def cohort_risk_summary() -> dict:
    """Triage the whole held-out cohort into ready / borderline / at-risk bands
    for a manager. Counts come from calibrated probabilities, not raw scores.
    """
    cohort, _, test_idx = _state()
    ids = [str(lid) for lid in cohort.learner_id[test_idx]]
    estimates = _estimate(ids)
    bands = {"ready": 0, "borderline": 0, "at_risk": 0}
    for e in estimates:
        if e.is_ready:
            bands["ready"] += 1
        elif e.calibrated_prob >= DEFAULT_CALIBRATION.readiness_threshold:
            bands["borderline"] += 1
        else:
            bands["at_risk"] += 1
    return {
        "cohort_size": len(estimates),
        "bands": bands,
        "threshold": DEFAULT_CALIBRATION.readiness_threshold,
        "note": "borderline = point estimate clears threshold but CI lower bound does not.",
    }


# --- Work IQ / Fabric IQ: clearly-labeled synthetic patterns ------------------

def work_iq_study_capacity(learner_id: str) -> dict:
    """[SYNTHETIC Work IQ pattern] Estimate weekly study hours a learner can
    realistically commit, derived from calendar/meeting load. In production this
    would read Microsoft 365 Work IQ signals; here it is deterministic synthetic
    data so the orchestration is demoable offline.
    """
    seed = abs(hash(learner_id)) % 1000
    hours = 2 + (seed % 9)  # 2-10 hrs/week
    return {"learner_id": learner_id, "weekly_study_hours": hours, "source": "synthetic:work_iq"}


def fabric_iq_skill_gap(topic: str) -> dict:
    """[SYNTHETIC Fabric IQ pattern] Return org-wide pass rate for an exam topic,
    standing in for a Fabric IQ analytics query over enterprise skilling data.
    """
    seed = abs(hash(topic)) % 100
    org_pass_rate = round(0.45 + seed / 250, 2)  # 0.45-0.85
    return {"topic": topic, "org_pass_rate": org_pass_rate, "source": "synthetic:fabric_iq"}

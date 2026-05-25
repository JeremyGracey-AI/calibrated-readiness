#!/usr/bin/env python3
"""Generate the synthetic cohort and write data/learners.csv.

    python scripts/generate_data.py

Useful on its own (e.g. to seed the Foundry IQ knowledge base or inspect the
two-tier ground truth) without running the full calibration benchmark.
"""

from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibrated_readiness.config import DEFAULT_SIM
from calibrated_readiness.synthetic_data import generate_cohort


def main() -> None:
    cohort = generate_cohort(DEFAULT_SIM)
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "learners.csv")
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["learner_id", "true_pass_prob", "outcome", "raw_score"])
        for i in range(len(cohort)):
            writer.writerow([
                cohort.learner_id[i],
                round(float(cohort.true_pass_prob[i]), 4),
                int(cohort.outcome[i]),
                round(float(cohort.raw_score[i]), 4),
            ])
    print(f"wrote {len(cohort)} learners -> {path}")
    print(f"observed pass rate = {cohort.outcome.mean():.3f}")


if __name__ == "__main__":
    main()

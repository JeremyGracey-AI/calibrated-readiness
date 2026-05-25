#!/usr/bin/env python3
"""The 60-second verification.

    python scripts/run_calibration.py

Generates the cohort, fits the calibrator on a held-out split, and writes
data/reliability.png + data/metrics.json. Prints the headline ECE reduction.
No Azure, no network, no API keys - this is the falsifiable core of the project.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibrated_readiness.config import DEFAULT_CALIBRATION, DEFAULT_SIM
from calibrated_readiness.pipeline import run_benchmark, write_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the calibration benchmark.")
    parser.add_argument("--method", choices=["temperature", "isotonic"], default="temperature")
    parser.add_argument("--out", default="data", help="output directory")
    args = parser.parse_args()

    result, cohort, calibrator, test_idx = run_benchmark(
        DEFAULT_SIM, DEFAULT_CALIBRATION, args.method
    )
    paths = write_artifacts(
        args.out, DEFAULT_SIM, DEFAULT_CALIBRATION, result, cohort, calibrator, test_idx
    )

    print("=" * 68)
    print("CALIBRATED READINESS - calibration benchmark")
    print("=" * 68)
    print(result.headline())
    print(f"  MCE   {result.raw_mce:.3f} -> {result.cal_mce:.3f}")
    print(f"  Brier {result.raw_brier:.3f} -> {result.cal_brier:.3f}")
    if result.temperature is not None:
        print(f"  fitted temperature T = {result.temperature:.2f} (>1 => was overconfident)")
    print(f"  cohort base pass rate = {result.base_rate:.2f}  (n_test={result.n_test})")
    print("-" * 68)
    print("artifacts:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print("=" * 68)


if __name__ == "__main__":
    main()

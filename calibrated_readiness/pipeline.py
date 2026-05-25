"""End-to-end calibration benchmark: data -> calibrate -> evaluate -> artifacts.

This is the single source of truth shared by the CLI (`scripts/run_calibration.py`)
and the agent's `assess_readiness` tool, so the demo and the numbers can never
drift apart.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass

import numpy as np

from .calibration import Calibrator, Method, fit_calibrator
from .config import CalibrationConfig, SimConfig
from .metrics import (
    brier_score,
    expected_calibration_error,
    max_calibration_error,
    reliability_table,
)
from .reliability import plot_reliability
from .synthetic_data import Cohort, generate_cohort, train_test_split


@dataclass(frozen=True)
class BenchmarkResult:
    method: Method
    gain: float
    n_bins: int
    n_train: int
    n_test: int
    raw_ece: float
    cal_ece: float
    ece_reduction_pct: float
    raw_mce: float
    cal_mce: float
    raw_brier: float
    cal_brier: float
    temperature: float | None
    base_rate: float  # observed pass rate in the test cohort

    def headline(self) -> str:
        return (
            f"ECE {self.raw_ece:.3f} -> {self.cal_ece:.3f} "
            f"({self.ece_reduction_pct:.0f}% lower) on the held-out cohort "
            f"[method={self.method}, gain={self.gain}, bins={self.n_bins}]"
        )


def run_benchmark(
    sim: SimConfig, cal: CalibrationConfig, method: Method
) -> tuple[BenchmarkResult, Cohort, Calibrator, np.ndarray]:
    """Run the benchmark in memory. Returns the result plus the objects the
    caller needs to write artifacts or score individual learners."""
    cohort = generate_cohort(sim)
    train_idx, test_idx = train_test_split(cohort, cal.test_fraction, cal.seed)

    calibrator = fit_calibrator(
        cohort.raw_score[train_idx], cohort.outcome[train_idx], method
    )

    raw_test = cohort.raw_score[test_idx]
    cal_test = calibrator.predict(raw_test)
    y_test = cohort.outcome[test_idx]

    raw_ece = expected_calibration_error(raw_test, y_test, cal.n_bins)
    cal_ece = expected_calibration_error(cal_test, y_test, cal.n_bins)
    reduction = 0.0 if raw_ece == 0 else 100 * (raw_ece - cal_ece) / raw_ece

    result = BenchmarkResult(
        method=method,
        gain=sim.gain,
        n_bins=cal.n_bins,
        n_train=len(train_idx),
        n_test=len(test_idx),
        raw_ece=raw_ece,
        cal_ece=cal_ece,
        ece_reduction_pct=reduction,
        raw_mce=max_calibration_error(raw_test, y_test, cal.n_bins),
        cal_mce=max_calibration_error(cal_test, y_test, cal.n_bins),
        raw_brier=brier_score(raw_test, y_test),
        cal_brier=brier_score(cal_test, y_test),
        temperature=calibrator.temperature,
        base_rate=float(y_test.mean()),
    )
    return result, cohort, calibrator, test_idx


def write_artifacts(
    out_dir: str,
    sim: SimConfig,
    cal: CalibrationConfig,
    result: BenchmarkResult,
    cohort: Cohort,
    calibrator: Calibrator,
    test_idx: np.ndarray,
) -> dict[str, str]:
    """Persist learners.csv, reliability.png and metrics.json. Returns paths."""
    os.makedirs(out_dir, exist_ok=True)

    raw_test = cohort.raw_score[test_idx]
    cal_test = calibrator.predict(raw_test)
    y_test = cohort.outcome[test_idx]

    raw_table = reliability_table(raw_test, y_test, cal.n_bins, cal.ci_level)
    cal_table = reliability_table(cal_test, y_test, cal.n_bins, cal.ci_level)

    png_path = os.path.join(out_dir, "reliability.png")
    plot_reliability(raw_table, cal_table, result.raw_ece, result.cal_ece, png_path)

    csv_path = os.path.join(out_dir, "learners.csv")
    calibrated_all = calibrator.predict(cohort.raw_score)
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["learner_id", "true_pass_prob", "outcome", "raw_score", "calibrated_prob"]
        )
        for i in range(len(cohort)):
            writer.writerow([
                cohort.learner_id[i],
                round(float(cohort.true_pass_prob[i]), 4),
                int(cohort.outcome[i]),
                round(float(cohort.raw_score[i]), 4),
                round(float(calibrated_all[i]), 4),
            ])

    json_path = os.path.join(out_dir, "metrics.json")
    with open(json_path, "w") as fh:
        json.dump(
            {"sim": asdict(sim), "calibration": asdict(cal), "result": asdict(result)},
            fh,
            indent=2,
        )

    return {"reliability_png": png_path, "learners_csv": csv_path, "metrics_json": json_path}

"""Render the reliability diagram - the 60-second verification artifact.

Two panels (raw vs calibrated) on the held-out test set. Each point is a bin:
x = mean predicted probability, y = observed pass rate, with a Wilson 95% error
bar. The dashed diagonal is perfect calibration. A well-calibrated panel has its
points hugging the diagonal and the diagonal passing through the error bars.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless: write a PNG, never open a window
import matplotlib.pyplot as plt
import numpy as np

from .metrics import Bin


def _draw_panel(ax: plt.Axes, table: list[Bin], title: str, ece: float) -> None:
    ax.plot([0, 1], [0, 1], "--", color="#888", lw=1, label="perfect calibration")

    xs, ys, lo_err, hi_err = [], [], [], []
    for b in table:
        if b.count == 0:
            continue
        xs.append(b.mean_predicted)
        ys.append(b.observed_rate)
        lo_err.append(b.observed_rate - b.wilson_lo)
        hi_err.append(b.wilson_hi - b.observed_rate)

    ax.errorbar(
        xs, ys, yerr=[lo_err, hi_err], fmt="o", color="#1f6feb",
        ecolor="#9db8e0", elinewidth=1.5, capsize=3, ms=6, label="observed (95% Wilson)",
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.set_xlabel("predicted P(pass)")
    ax.set_ylabel("observed pass rate")
    ax.set_title(f"{title}\nECE = {ece:.3f}", fontsize=11)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.grid(alpha=0.25)


def plot_reliability(
    raw_table: list[Bin],
    cal_table: list[Bin],
    raw_ece: float,
    cal_ece: float,
    out_path: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    _draw_panel(axes[0], raw_table, "Raw readiness score", raw_ece)
    _draw_panel(axes[1], cal_table, "Calibrated readiness", cal_ece)
    reduction = 0.0 if raw_ece == 0 else 100 * (raw_ece - cal_ece) / raw_ece
    fig.suptitle(
        f"Calibrated Readiness - reliability on held-out cohort "
        f"(ECE {raw_ece:.3f} -> {cal_ece:.3f}, {reduction:.0f}% lower)",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=130)
    plt.close(fig)

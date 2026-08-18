"""Calibrated Readiness — interactive demo (Hugging Face Spaces / local entrypoint).

An in-browser front end for the falsifiable core: adjust the synthetic cohort and
the calibration knobs, run the real `run_benchmark` pipeline, and watch Expected
Calibration Error drop on a held-out split — with the reliability diagram that
proves it. No Azure, no keys; this is the same cloud-free path as
`python scripts/run_calibration.py`.
"""

from __future__ import annotations

import os
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")  # headless: render figures without a display

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr

from calibrated_readiness.config import CalibrationConfig, SimConfig
from calibrated_readiness.pipeline import run_benchmark, write_artifacts


def run(
    gain: float,
    n_bins: int,
    n_learners: int,
    discrimination: float,
    practice_noise: float,
    seed: int,
    method: str,
) -> tuple[str, str]:
    """Run one calibration benchmark and return (reliability_png_path, summary_md)."""
    sim = SimConfig(
        n_learners=int(n_learners),
        discrimination=float(discrimination),
        practice_noise=float(practice_noise),
        gain=float(gain),
        seed=int(seed),
    )
    cal = CalibrationConfig(n_bins=int(n_bins), seed=int(seed))
    result, cohort, calibrator, test_idx = run_benchmark(sim, cal, method)

    out_dir = tempfile.mkdtemp(prefix="cr_demo_")
    paths = write_artifacts(out_dir, sim, cal, result, cohort, calibrator, test_idx)

    t = result.temperature
    t_line = (
        f"| fitted temperature | **T = {t:.2f}** "
        f"({'was overconfident' if t and t > 1 else 'well-scaled'}) |\n"
        if t is not None
        else ""
    )
    summary = (
        f"### {result.headline()}\n\n"
        "| metric | raw → calibrated |\n"
        "|---|---|\n"
        f"| **Expected Calibration Error** | **{result.raw_ece:.3f} → {result.cal_ece:.3f}** "
        f"(**{result.ece_reduction_pct:.0f}% lower**) |\n"
        f"| Max Calibration Error | {result.raw_mce:.3f} → {result.cal_mce:.3f} |\n"
        f"| Brier score | {result.raw_brier:.3f} → {result.cal_brier:.3f} |\n"
        f"{t_line}"
        f"| cohort base pass-rate | {result.base_rate:.2f} (n_test = {result.n_test}) |\n\n"
        f"*Method: {method}. Every number is computed on a held-out split of a freshly "
        f"generated cohort — change a slider and re-run to falsify it yourself.*"
    )
    return paths["reliability_png"], summary


with gr.Blocks(title="Calibrated Readiness") as demo:
    gr.Markdown(
        "# Calibrated Readiness\n"
        "**Readiness as a *measured quantity with a confidence interval* — verify it in "
        "60 seconds.** A raw pass-probability score is usually *overconfident*; a thin "
        "temperature-scaling layer fixes it, and Expected Calibration Error (ECE) measures "
        "whether the fix is real. Turn the knobs, run the real benchmark, read the diagram."
    )
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("**The overconfidence knob**")
            gain = gr.Slider(0.5, 3.0, value=1.9, step=0.1, label="gain  (>1 = raw score overconfident)")
            n_bins = gr.Slider(5, 20, value=10, step=1, label="reliability bins")
            method = gr.Radio(["temperature", "isotonic"], value="temperature", label="calibration method")
            with gr.Accordion("cohort parameters", open=False):
                n_learners = gr.Slider(100, 2000, value=600, step=50, label="n_learners")
                discrimination = gr.Slider(0.5, 3.0, value=1.7, step=0.1, label="discrimination (IRT a)")
                practice_noise = gr.Slider(0.1, 1.5, value=0.55, step=0.05, label="practice noise")
                seed = gr.Slider(0, 100, value=7, step=1, label="seed")
            run_btn = gr.Button("Run the 60-second verification", variant="primary")
        with gr.Column(scale=2):
            plot = gr.Image(label="Reliability diagram (raw vs calibrated)", type="filepath")
            summary = gr.Markdown()

    inputs = [gain, n_bins, n_learners, discrimination, practice_noise, seed, method]
    run_btn.click(run, inputs=inputs, outputs=[plot, summary])
    gr.Examples(
        examples=[
            [1.9, 10, 600, 1.7, 0.55, 7, "temperature"],
            [2.6, 10, 600, 1.7, 0.55, 7, "temperature"],
            [1.1, 12, 800, 2.0, 0.40, 7, "isotonic"],
        ],
        inputs=inputs,
        label="Presets: default · badly overconfident · already-good",
    )
    demo.load(run, inputs=inputs, outputs=[plot, summary])  # render once on open


if __name__ == "__main__":
    demo.launch()

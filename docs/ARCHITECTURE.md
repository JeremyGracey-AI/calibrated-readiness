# Architecture

## One idea, enforced everywhere

**Readiness is a measured quantity.** Every design choice serves that: a single
calibration pipeline produces the numbers, the agents are forbidden from
inventing readiness, and the headline artifact is a falsification test (the
reliability diagram), not a dashboard.

## Data flow

```
SimConfig ──▶ synthetic_data.generate_cohort ──▶ Cohort(ability, true_pass_prob, outcome, raw_score)
                                                      │
                                  train/test split (calibrate on train only)
                                                      │
            calibration.fit_calibrator(method) ──▶ Calibrator  ──▶ calibrated probabilities
                                                      │                     │
                       metrics.reliability_table + ECE/MCE/Brier     calibration.readiness_with_ci
                                                      │                     │
                       reliability.plot_reliability  │              ReadinessEstimate(prob, CI, ready)
                                                      ▼                     ▼
                                  data/reliability.png + metrics.json   tools.assess_readiness
                                                                            │
                                                              agents (readiness, triage) quote these
```

The crucial edge: `tools.assess_readiness` and `tools.cohort_risk_summary` read
from `pipeline.run_benchmark` — the *same* function the CLI verification uses. An
agent can never surface a readiness number that the reliability diagram has not
already justified.

## Why these components

**Two-tier ground truth (`synthetic_data.py`).** A latent ability `theta` yields a
true pass probability `p_true` (tier 1, hidden) and a realized exam outcome
`y ~ Bernoulli(p_true)` (tier 2, the label). The system only sees a noisy,
overconfident `raw_score`. This separation is what makes calibration *testable*:
we calibrate against `y` and check honesty against held-out `y`.

**Temperature scaling as the default (`calibration.py`).** The miscalibration here
is over-confidence — a slope problem in logit space — so a one-parameter
temperature is the correct inductive bias and is interpretable (T>1 ⇒ the raw
score was overconfident). Isotonic regression is offered as a non-parametric
alternative, but on a 300-learner split it overfits (its MCE explodes), which the
demo shows on purpose.

**Confidence intervals by bootstrap.** Refitting the calibrator on resampled
training data propagates *calibration* uncertainty into each learner's number.
"Ready" requires the **lower** CI bound to clear the threshold, so the decision
survives that uncertainty.

**Wilson bands on the diagram (`metrics.py`).** Per-bin observed rates get Wilson
score intervals — well-behaved for the small counts and near-0/1 rates typical of
reliability bins, unlike the normal approximation.

## Agent layer

Four agents (`agents.py`) over one chat client, routed by `HandoffBuilder`
(`orchestration.py`). The triage/Manager-Insights agent is the start node and the
only router. Foundry IQ (`foundry_iq.py`) grounds the knowledge-heavy agents
(study_plan, practice) via an agentic-mode Azure AI Search context provider.

Handoff orchestration is chosen over sequential/concurrent because the routing is
data-dependent and cyclic (the "readiness loop"): triage → readiness → (not ready)
→ back to triage → study_plan → practice. That conditional topology is the whole
point of the handoff pattern.

## Boundaries

The package is split so the **verifiable core has zero cloud dependencies**.
`config / synthetic_data / metrics / calibration / reliability / pipeline / tools`
import only numpy/scipy/sklearn/matplotlib. The Azure SDK and Agent Framework are
imported lazily, inside functions, only in `foundry_iq.py` and the agent builders —
so `import calibrated_readiness.agents` succeeds even with no cloud packages
installed, and the 60-second verification never depends on a tenant.

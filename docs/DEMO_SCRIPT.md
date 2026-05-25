# Demo Script & Judging Narrative

A 4-minute run that lands the differentiator. The whole thing works offline, so a
flaky tenant or Wi-Fi can never sink the demo.

---

## The 20-second hook

> "Every other submission tells a learner *'you're probably ready.'* Ours tells
> them *'your calibrated probability of passing is 0.78, give or take 8 points —
> borderline,'* and then **proves that number is honest** in 60 seconds. We treat
> readiness as a measurement, with a confidence interval and a falsification test."

---

## Beat 1 — the falsifiable claim (60 seconds, run live)

```bash
pip install -r requirements.txt
python scripts/run_calibration.py
```

Point at the output and the diagram (`data/reliability.png`):

> "600 synthetic learners with known outcomes. The **left** panel is the raw
> practice score — see how the points sag off the diagonal? That's
> over-confidence: when it says 85%, only ~70% actually pass. The **right** panel
> is after calibration — points hug the diagonal, and the dashed perfect-calibration
> line falls inside the 95% Wilson bands. ECE drops from **0.16 to 0.07**. The
> fitted temperature is **2.4**, which literally measures how overconfident the raw
> score was. You just watched the claim get verified."

Optional kill-shot for skeptics:

```bash
python scripts/run_calibration.py --method isotonic   # MCE blows up to ~0.78
```

> "We're not cherry-picking a method — temperature scaling wins here for a
> principled reason, and we can show the alternative overfitting."

## Beat 2 — readiness as a decision (30 seconds)

```bash
python app/demo.py --mode offline
```

> "Same pipeline, now per-learner. L0204: P(pass) 0.99, CI [0.98, 1.00] — **Ready**,
> schedule the exam. L0250: 0.01 — **At-risk**, do not. And the manager view triages
> the whole cohort into ready / borderline / at-risk. 'Ready' requires the
> *lower* confidence bound to clear 0.80 — so the call survives our own uncertainty."

## Beat 3 — the agents & reasoning (60 seconds)

Walk the architecture (README diagram), no live cloud needed:

> "Four agents, routed by **handoff orchestration**. The Manager-Insights agent
> triages and routes. The Calibration agent reports the number — and it physically
> *cannot* invent one; it calls the same verified pipeline. Study-plan and Practice
> are grounded in **Foundry IQ** — agentic, multi-hop retrieval over our knowledge
> base. The reasoning loop is genuinely dynamic: 'not ready' bounces control back
> to triage to build a plan, then to practice. That's why handoff, not a fixed
> sequence."

If a tenant is available, run `python app/demo.py --mode live`. If not, say so
plainly and show the code path — the judges can read `orchestration.py`.

## Beat 4 — the close (20 seconds)

> "The graded differentiator — calibrated, falsifiable readiness — runs with zero
> cloud and is unit-tested. The agent layer is built against the *current,
> verified* Agent Framework API, and we documented exactly what a live deploy
> needs, including a version-pin gotcha we already found. We measured readiness.
> We didn't vibe it."

---

## Anticipated questions

- **"Is 66%/55% ECE reduction real or tuned?"** It's real on *this* synthetic
  benchmark and depends on two documented knobs (simulator `gain`, bin count). We
  quote it as a benchmark result, not a law. The *method* (lower ECE after
  calibration) is robust, which the test suite asserts.
- **"Why synthetic data?"** Calibration needs labeled outcomes at scale; synthetic
  data with a known generative process lets us *prove* the method recovers honest
  probabilities. The same pipeline drops onto real pass/fail logs unchanged.
- **"Did you deploy to Azure?"** We built locally, packaged for deployment, and
  documented the hosted-agent path. Live deployment was deliberately out of scope;
  see `docs/LIVE_FOUNDRY_NOTES.md`.
- **"Why should a manager trust it?"** Because it's falsifiable. The reliability
  diagram is the audit: if the probabilities were dishonest, the points would miss
  the diagonal and the Wilson bands would tell you.

---

## Pre-demo checklist
- [ ] `pip install -r requirements.txt` in a clean env
- [ ] `python scripts/run_calibration.py` renders `data/reliability.png`
- [ ] `pytest -q` is green
- [ ] `python app/demo.py --mode offline` prints the three beats
- [ ] (optional) `.env` filled + `requirements-agents.txt` installed for `--mode live`

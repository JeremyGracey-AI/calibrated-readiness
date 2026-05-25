# Certification Readiness Policy

*Synthetic knowledge document for the Calibrated Readiness Foundry IQ knowledge base.*

This policy defines what "ready" means in the program and is the rule the agents
enforce. It is deliberately written around a **calibrated probability**, because a
raw practice-test percentage is not a trustworthy predictor of the real outcome.

## Definition of readiness
A learner is **certified-ready** only when the **lower bound of the 95% confidence
interval** on their calibrated probability of passing is **at or above 0.80**.

- We use the *lower CI bound*, not the point estimate, so the decision survives
  our uncertainty about the calibration map. A learner at P=0.83 with a wide
  interval [0.71, 0.92] is **borderline**, not ready.
- Bands:
  - **Ready**: CI lower bound >= 0.80
  - **Borderline**: point estimate >= 0.80 but CI lower bound < 0.80
  - **At-risk**: point estimate < 0.80

## Why calibration is required
Practice-engine scores are systematically overconfident. Before any readiness
decision, scores must be calibrated against historical pass/fail outcomes and the
calibration quality reported as Expected Calibration Error (ECE) on a held-out
cohort. A program may not act on readiness numbers whose ECE exceeds 0.10 on the
current cohort without flagging the estimate as low-confidence.

## Manager guidance
- Schedule the exam for Ready learners.
- For Borderline learners, fund one more focused study cycle on the highest-weight
  weak domain, then re-assess.
- For At-risk learners, build a full study plan and do not schedule the exam yet.
- Always communicate the interval, not just the number. "78% +/- 9%" sets honest
  expectations; "78%" does not.

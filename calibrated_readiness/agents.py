"""Phase 4 - the four agents.

Built against agent-framework-core 1.6.0: an agent is `Agent(client, instructions=...,
name=..., tools=[...], context_providers=[...])`. (In the Dec-2025 preview this
class was `ChatAgent(chat_client=...)`; see docs/LIVE_FOUNDRY_NOTES.md for the
migration. We target the current GA symbol.)

  triage      Manager Insights / risk-triage router. The conversation entry
              point; decides who needs what based on calibrated readiness.
  readiness   Calibration agent. Reports calibrated P(pass) + CI from the
              verified pipeline (assess_readiness tool).
  study_plan  Builds a plan for under-ready learners, grounded in Foundry IQ.
  practice    Generates targeted practice questions, grounded in Foundry IQ.
"""

from __future__ import annotations

from typing import Any

from .tools import (
    assess_readiness,
    cohort_risk_summary,
    fabric_iq_skill_gap,
    work_iq_study_capacity,
)

TRIAGE_INSTRUCTIONS = """You are the Manager Insights agent for an enterprise \
certification program. You triage learners by readiness risk and route work.

Use cohort_risk_summary for cohort-level questions. For an individual, hand off \
to the readiness agent to get a calibrated estimate before recommending action. \
Route at-risk learners to study_plan, and learners with specific weak topics to \
practice. Never invent readiness numbers - rely on the readiness agent. \
Speak to a manager: concise, decision-oriented, honest about uncertainty."""

READINESS_INSTRUCTIONS = """You are the Calibration agent. Given a learner_id, \
call assess_readiness and report the calibrated probability of passing WITH its \
95% confidence interval. Always state the interval, not just the point estimate, \
and explain that 'ready' requires the lower bound to clear the threshold. If the \
learner is not ready, hand back to triage so a study plan can be built."""

STUDY_PLAN_INSTRUCTIONS = """You are the Study Plan agent. Build a focused, \
realistic study plan for a learner who is not yet ready. Ground every \
recommendation in the knowledge base (exam blueprint, study resources, readiness \
policy) via your retrieval context. Use work_iq_study_capacity to fit the plan to \
the hours the learner actually has, and fabric_iq_skill_gap to prioritise topics \
where the org is weak. Cite the knowledge sources you used."""

PRACTICE_INSTRUCTIONS = """You are the Practice Question agent. Generate targeted \
practice questions for the learner's weak topics, grounded in the exam blueprint \
from your retrieval context. Match question difficulty to the blueprint weighting. \
Provide an answer key with short explanations."""


def build_agents(chat_client: Any, foundry_context: Any | None = None) -> dict[str, Any]:
    """Construct the four agents from a chat client and an optional Foundry IQ
    context provider. Knowledge-grounded agents receive the context provider;
    number-driven agents rely on verified tools instead."""
    from agent_framework import Agent

    grounding = [foundry_context] if foundry_context is not None else None

    triage = Agent(
        chat_client,
        instructions=TRIAGE_INSTRUCTIONS,
        name="triage",
        description="Manager Insights router: triages learners by readiness risk.",
        tools=[cohort_risk_summary],
    )
    readiness = Agent(
        chat_client,
        instructions=READINESS_INSTRUCTIONS,
        name="readiness",
        description="Reports calibrated pass probability with a confidence interval.",
        tools=[assess_readiness],
    )
    study_plan = Agent(
        chat_client,
        instructions=STUDY_PLAN_INSTRUCTIONS,
        name="study_plan",
        description="Builds a knowledge-grounded study plan for under-ready learners.",
        tools=[work_iq_study_capacity, fabric_iq_skill_gap],
        context_providers=grounding,
    )
    practice = Agent(
        chat_client,
        instructions=PRACTICE_INSTRUCTIONS,
        name="practice",
        description="Generates targeted, blueprint-grounded practice questions.",
        context_providers=grounding,
    )
    return {
        "triage": triage,
        "readiness": readiness,
        "study_plan": study_plan,
        "practice": practice,
    }

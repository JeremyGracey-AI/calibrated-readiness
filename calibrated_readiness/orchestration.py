"""Phase 4 - handoff orchestration (the readiness loop).

We use HandoffBuilder (agent-framework-orchestrations 1.0.0rc2) rather than a
sequential or concurrent pattern because routing here is genuinely dynamic: the
triage agent decides, per learner, whether to pull a calibrated estimate, build a
study plan, or generate practice - and the readiness agent can bounce control
back when someone isn't ready yet. That conditional, context-driven topology is
exactly what handoff orchestration is for.

Topology (start = triage):
    triage     -> readiness, study_plan, practice
    readiness  -> triage, study_plan        (loop back when not ready)
    study_plan -> practice, triage
    practice   -> triage
"""

from __future__ import annotations

from typing import Any


def build_readiness_workflow(agents: dict[str, Any]) -> Any:
    """Wire the four agents into a handoff Workflow. Returns a Workflow."""
    from agent_framework.orchestrations import HandoffBuilder

    triage = agents["triage"]
    readiness = agents["readiness"]
    study_plan = agents["study_plan"]
    practice = agents["practice"]

    return (
        HandoffBuilder(
            name="readiness-loop",
            participants=[triage, readiness, study_plan, practice],
        )
        .with_start_agent(triage)
        .add_handoff(triage, [readiness, study_plan, practice])
        .add_handoff(readiness, [triage, study_plan])
        .add_handoff(study_plan, [practice, triage])
        .add_handoff(practice, [triage])
        .build()
    )


def build_orchestrator_agent(agents: dict[str, Any]) -> Any:
    """Expose the whole readiness loop as a single agent (WorkflowAgent), so it
    can be hosted or composed like any other agent.

    NOTE: `as_agent` is a method on the built Workflow, not on HandoffBuilder -
    a detail worth knowing because the kwargs differ from a plain agent (see
    docs/LIVE_FOUNDRY_NOTES.md). Signature in rc2:
        Workflow.as_agent(name=None, *, description=None, context_providers=None, **kwargs)
    """
    workflow = build_readiness_workflow(agents)
    return workflow.as_agent(
        name="calibrated-readiness",
        description=(
            "Multi-agent certification readiness system with a calibrated, "
            "falsifiable estimate of exam-readiness."
        ),
    )

#!/usr/bin/env python3
"""End-to-end demo.

    python app/demo.py                # auto: live if Azure env is set, else offline
    python app/demo.py --mode offline # force the cloud-free path (always works)
    python app/demo.py --mode live    # force the Foundry/agent path

Offline mode tells the whole calibrated-readiness story using only the verified
pipeline and the pure tools - no Azure, no keys. Live mode runs the four agents
through the handoff orchestration grounded in Foundry IQ.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _azure_configured() -> bool:
    return all(
        os.environ.get(k)
        for k in (
            "FOUNDRY_PROJECT_ENDPOINT",
            "FOUNDRY_MODEL_DEPLOYMENT",
            "AZURE_SEARCH_ENDPOINT",
            "FOUNDRY_KNOWLEDGE_BASE",
        )
    )


def run_offline() -> None:
    from calibrated_readiness.config import DEFAULT_CALIBRATION, DEFAULT_SIM
    from calibrated_readiness.pipeline import run_benchmark
    from calibrated_readiness.tools import assess_readiness, cohort_risk_summary

    result, cohort, _, _ = run_benchmark(DEFAULT_SIM, DEFAULT_CALIBRATION, "temperature")
    print("=" * 70)
    print("CALIBRATED READINESS - offline demo (no Azure required)")
    print("=" * 70)
    print("1) Calibration benchmark")
    print("   " + result.headline())

    # Pick a clearly-ready and a clearly-at-risk learner to contrast.
    cal = run_benchmark(DEFAULT_SIM, DEFAULT_CALIBRATION, "temperature")[2]
    probs = cal.predict(cohort.raw_score)
    ready_id = str(cohort.learner_id[probs.argmax()])
    risk_id = str(cohort.learner_id[probs.argmin()])

    print("\n2) Individual readiness (calibrated, with CI)")
    for lid in (ready_id, risk_id):
        r = assess_readiness(lid)
        print(
            f"   {r['learner_id']}: P(pass)={r['calibrated_pass_probability']} "
            f"CI95={r['ci95']} -> {r['decision'].upper()}"
        )

    print("\n3) Manager Insights - cohort triage")
    summary = cohort_risk_summary()
    print(f"   {summary['bands']}  (n={summary['cohort_size']}, "
          f"threshold={summary['threshold']})")
    print("=" * 70)
    print("The numbers above come from the same pipeline the reliability diagram")
    print("verifies. Run: python scripts/run_calibration.py")


async def run_live() -> None:
    from calibrated_readiness.agents import build_agents
    from calibrated_readiness.foundry_iq import (
        build_chat_client,
        build_credential,
        build_foundry_iq_context,
    )
    from calibrated_readiness.orchestration import build_orchestrator_agent
    from calibrated_readiness.settings import AzureSettings

    settings = AzureSettings.from_env()
    credential = build_credential()
    async with credential:
        async with (
            build_foundry_iq_context(settings, credential) as foundry,
            build_chat_client(settings, credential) as client,
        ):
            agents = build_agents(client, foundry)
            orchestrator = build_orchestrator_agent(agents)
            prompt = (
                "I'm a manager. Triage learner L0007 for the certification: is "
                "this person ready, and if not, what should they do next?"
            )
            print("=" * 70)
            print("CALIBRATED READINESS - live demo (Foundry + handoff orchestration)")
            print("=" * 70)
            print(f"> {prompt}\n")
            response = await orchestrator.run(prompt)
            print(getattr(response, "text", response))


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrated Readiness demo")
    parser.add_argument("--mode", choices=["auto", "offline", "live"], default="auto")
    args = parser.parse_args()

    if args.mode == "offline" or (args.mode == "auto" and not _azure_configured()):
        if args.mode == "auto":
            print("(Azure not configured - running offline demo. "
                  "Set vars from .env.example for the live path.)\n")
        run_offline()
        return

    asyncio.run(run_live())


if __name__ == "__main__":
    main()

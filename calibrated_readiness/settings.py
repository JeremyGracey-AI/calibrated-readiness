"""Azure / Foundry connection settings, validated at the boundary.

Nothing here imports the Azure SDK, so the runnable calibration core never
depends on cloud credentials. Only the agent layer reads these.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AzureSettings:
    project_endpoint: str  # Azure AI Foundry project endpoint
    model_deployment_name: str  # e.g. "gpt-4o" (Foundry IQ requires Azure OpenAI)
    search_endpoint: str  # Azure AI Search endpoint backing Foundry IQ
    knowledge_base_name: str  # the Foundry IQ knowledge base to ground on
    retrieval_reasoning_effort: str = "medium"  # minimal | low | medium

    @staticmethod
    def from_env() -> "AzureSettings":
        """Load from environment (see .env.example). Asserts loudly if missing -
        a clear error here beats an opaque auth failure deep in an agent call.
        """
        def need(key: str) -> str:
            value = os.environ.get(key, "").strip()
            assert value, f"missing required environment variable: {key}"
            return value

        return AzureSettings(
            project_endpoint=need("FOUNDRY_PROJECT_ENDPOINT"),
            model_deployment_name=need("FOUNDRY_MODEL_DEPLOYMENT"),
            search_endpoint=need("AZURE_SEARCH_ENDPOINT"),
            knowledge_base_name=need("FOUNDRY_KNOWLEDGE_BASE"),
            retrieval_reasoning_effort=os.environ.get(
                "FOUNDRY_RETRIEVAL_EFFORT", "medium"
            ).strip(),
        )

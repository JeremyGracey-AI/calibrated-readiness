"""Foundry IQ wiring - the one IQ layer this project implements for real.

Foundry IQ is the Azure AI Search Context Provider in the Microsoft Agent
Framework: agentic, multi-hop retrieval over a Knowledge Base, injected into an
agent as a context provider. Pattern verified against agent-framework-azure-ai
(see the Microsoft Foundry blog, "Foundry IQ in Microsoft Agent Framework").

All Azure imports are lazy so importing this module never requires the cloud
SDK. The runnable calibration core stays cloud-free.
"""

from __future__ import annotations

from typing import Any

from .settings import AzureSettings


def build_credential() -> Any:
    """Managed-identity-first credential (keyless). Falls back to env/CLI/VS Code
    via DefaultAzureCredential's standard chain."""
    from azure.identity.aio import DefaultAzureCredential

    return DefaultAzureCredential()


def build_foundry_iq_context(settings: AzureSettings, credential: Any) -> Any:
    """Create the Foundry IQ context provider in agentic mode.

    Returns an `AzureAISearchContextProvider` to pass as `context_providers=[...]`
    on an agent. The caller owns the async lifecycle (use `async with`).
    Provided by the `agent-framework-azure-ai-search` package.
    """
    from agent_framework.azure import AzureAISearchContextProvider

    return AzureAISearchContextProvider(
        endpoint=settings.search_endpoint,
        knowledge_base_name=settings.knowledge_base_name,
        credential=credential,
        mode="agentic",  # Foundry IQ: query planning + multi-hop, not plain RAG
        retrieval_reasoning_effort=settings.retrieval_reasoning_effort,
    )


def build_chat_client(settings: AzureSettings, credential: Any) -> Any:
    """Create the Azure AI Foundry chat client used by every agent.

    Uses `AzureAIClient` from the `agent-framework-azure-ai` package. We target
    `AzureAIClient` (not the older `AzureAIAgentClient`, which is deprecated -
    it pins the V1 Agents Service API). Verified against the installed source:
    the credential kwarg is `credential=`, NOT the `async_credential=` shown in
    the Dec-2025 launch blog. See docs/LIVE_FOUNDRY_NOTES.md for the full matrix.
    """
    from agent_framework_azure_ai import AzureAIClient

    return AzureAIClient(
        project_endpoint=settings.project_endpoint,
        model_deployment_name=settings.model_deployment_name,
        credential=credential,
    )

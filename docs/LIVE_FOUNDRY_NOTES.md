# Live Foundry / Agent Framework — De-risking Notes

Everything in `foundry_iq.py`, `agents.py`, and `orchestration.py` targets a
*live* Azure AI Foundry endpoint, which we cannot exercise without a tenant. This
document is the pre-flight: the exact, **current** API (verified by introspecting
the installed packages — not copied from a blog), the bugs that the original
blog-based code almost certainly carried, and the one hard incompatibility you
must resolve before a live run.

> Verified against: `agent-framework-core 1.6.0`, `agent-framework-orchestrations
> 1.0.0rc2`, `agent-framework-azure-ai 1.0.0rc6`, `agent-framework-azure-ai-search
> 1.0.0b260521` (Python 3.10). API surfaces below were read directly from those
> installed packages on 2026-05-24.

---

## 0. The one thing that will stop a live run today (BLOCKER)

`agent-framework-azure-ai 1.0.0rc6` imports `BaseContextProvider` from
`agent_framework`, but `agent-framework-core 1.6.0` exports that base class as
**`ContextProvider`** (there is no `BaseContextProvider`). So:

```python
>>> import agent_framework_azure_ai
ImportError: cannot import name 'BaseContextProvider' from 'agent_framework'
```

The chat-client package and core are out of sync in the latest published set.
**Resolution options (pick one before `--mode live`):**

1. **Pin a matched pair.** Hold `agent-framework-azure-ai` back to the rc that was
   cut against core 1.6.0, or move `agent-framework-core` forward to the version
   rc6 targets. Check each package's `Requires-Dist` for the core pin:
   `pip show agent-framework-azure-ai | grep Requires`.
2. **Shim (last resort, local only).** Before importing the package, alias the
   symbol: `import agent_framework as af; af.BaseContextProvider = af.ContextProvider`.
   Use only to unblock a demo; fix the pins properly afterward.

The **Foundry IQ retrieval** package (`agent-framework-azure-ai-search`) imports
cleanly against core 1.6.0 — only the chat-client package has the clash.

---

## 1. API corrections vs. the Dec-2025 launch blog

The widely-cited "~20 lines of Python" Foundry IQ blog predates core 1.6.0. Code
written from it (very likely the shape of the original submission) breaks in
these specific ways. The repo already uses the corrected forms.

| What the blog shows | What core 1.6.0 / rc6 actually wants | Where |
| --- | --- | --- |
| `from agent_framework import ChatAgent` | `ChatAgent` is **not exported**. Use `from agent_framework import Agent`. | `agents.py` |
| `ChatAgent(chat_client=client, ...)` | `Agent(client, instructions=..., name=..., tools=..., context_providers=...)` — the client is **positional**, kwarg renamed. | `agents.py` |
| `from agent_framework.azure import AzureAIAgentClient` | Not re-exported by `agent_framework.azure` in 1.6.0. Import from `agent_framework_azure_ai`. And `AzureAIAgentClient` is **deprecated** (pins the V1 Agents Service). Use **`AzureAIClient`**. | `foundry_iq.py` |
| `AzureAIAgentClient(..., async_credential=cred)` | The credential kwarg is **`credential=`** (keyword-only), not `async_credential=`. | `foundry_iq.py` |
| `HandoffBuilder(...).as_agent(...)` | `as_agent` is **not on the builder**. Call `.build()` to get a `Workflow`, then `Workflow.as_agent(...)`. | `orchestration.py` |

---

## 2. Confirmed-correct API surfaces (use as-is)

**Agent construction** (`agent_framework.Agent.__init__`, abridged):

```python
Agent(client, instructions=None, *, id=None, name=None, description=None,
      tools=..., context_providers=..., middleware=..., ...)
```

Plain typed Python functions are valid `tools` — the framework infers the schema
from the signature + docstring (so `assess_readiness(learner_id: str) -> dict`
just works).

**HandoffBuilder** (`agent_framework.orchestrations`, rc2):

```python
HandoffBuilder(*, name=None, participants=None, description=None,
               checkpoint_storage=None, termination_condition=None,
               output_from=..., intermediate_output_from=None)
  .with_start_agent(agent)              # -> HandoffBuilder
  .add_handoff(source, targets, *, description=None)   # source/targets are Agent objects
  .with_autonomous_mode(...)            # optional
  .with_checkpointing(...)              # optional
  .with_termination_condition(...)      # optional
  .build()                              # -> Workflow
```

Note `add_handoff` takes **Agent instances**, not name strings. The
`HandoffAgentExecutor` auto-registers a handoff tool on each source agent from the
declared edges; related types you'll see in the event stream include
`HandoffSentEvent` and `HandoffAgentUserRequest`.

**Expose the workflow as an agent** (`Workflow.as_agent`):

```python
Workflow.as_agent(name=None, *, description=None, context_providers=None, **kwargs)
    -> WorkflowAgent
```

This **answers the original open question** ("does `as_agent` accept exactly these
kwargs in rc2?"): it accepts `name`, `description`, `context_providers`, and
`**kwargs` — it is permissive, so passing `name`/`description` is safe.

**Foundry IQ context provider** (`agent_framework.azure.AzureAISearchContextProvider`):

```python
AzureAISearchContextProvider(
    endpoint=..., knowledge_base_name=..., credential=...,
    mode="agentic",                       # vs "semantic"
    retrieval_reasoning_effort="medium",  # minimal | low | medium
)
```

Agentic mode requires an **Azure OpenAI** model deployment and a Knowledge Base.
The provider and the chat client are **async context managers** — drive them with
`async with`, as `app/demo.py:run_live` does.

---

## 3. Auth

Code uses `azure.identity.aio.DefaultAzureCredential` (managed-identity-first,
keyless). Before a live run:

- **Local:** `az login`; the credential chain picks up the CLI/VS Code identity.
- **Hosted:** assign a managed identity and grant it data-plane roles —
  *Search Index Data Reader* (or KB-appropriate role) on the Search service and
  the Foundry project's data-plane role. Keyless throughout; no secrets in the image.
- The credential is itself an async context manager (`async with credential:`).

---

## 4. The handoff event flow (untested, expected to need a tweak)

When you run the **Workflow directly** you consume a *stream of events*
(agent responses, `HandoffSentEvent`, user-request pauses). When you wrap it with
`as_agent`, the `WorkflowAgent` is meant to behave like a normal agent, so
`await orchestrator.run(prompt)` should return a response with `.text`.

`app/demo.py` reads `getattr(response, "text", response)` precisely because this
is the one place we expect a possible shape mismatch on first contact. If `.run`
on the `WorkflowAgent` instead returns a stream or a structured result, switch to
the streaming/`run_stream` form and collect the final assistant turn. This is the
single most likely "small fix on first live run."

---

## 5. First-live-run checklist

1. Resolve the §0 version clash (`pip show ... | grep Requires`, then re-pin).
2. `az login`; confirm `python -c "import agent_framework_azure_ai"` succeeds.
3. Create the Foundry IQ knowledge base from `knowledge/*.md`; set `.env`.
4. Smoke-test retrieval alone: a one-agent `Agent(client, context_providers=[ctx])`
   answering "what's in the knowledge base?" before adding handoff.
5. Add the handoff workflow; if `as_agent(...).run()` shape surprises you, see §4.
6. Only then wire the full four-agent loop.

The calibration core (the graded differentiator) needs none of the above and is
already verified — keep the live agent work on a branch so a tenant hiccup never
risks the part that works.

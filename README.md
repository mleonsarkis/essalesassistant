# ES Sales Agentic Assistant

An agentic AI assistant for sales teams. The system interprets user messages, dynamically selects the right capability ("skill"), invokes it through a structured tool registry, and composes a response — all with validation, enrichment, audit logging, metrics, and graceful error handling wired in as cross-cutting hooks. It ships with a Microsoft Bot Framework adapter so the same agent is reachable from Microsoft Teams and Telegram.

This project used to be a chatbot with hardcoded intent→function routing. It has been refactored into a four-layer agentic architecture so that adding a new capability never requires touching the agent or the bot transport.

## Architecture Overview

The system is composed of four clean layers plus an observability spine.

```
┌──────────────────────────────────────────────────────────────────────┐
│                      User (Teams / Telegram / API)                   │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ raw text + session id
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Agent Layer  —  agent/sales_agent.py                                │
│  LangChain AgentExecutor with OpenAI tool-calling.                   │
│  Knows *how to reason*, not what the tools do.                       │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ tool name + arguments
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MCP-style Tool Registry  —  mcp/registry.py, mcp/server.py          │
│  Discovery (list_tools), structured invocation, JSON-schema manifest.│
└──────────────────────────┬───────────────────────────────────────────┘
                           │ wrapped in hook pipeline
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Hooks Layer  —  hooks/*.py                                          │
│  pre:   JSON schema validation, argument enrichment                  │
│  post:  structured audit log, in-memory metrics                      │
│  error: bounded retry, graceful fallback result                      │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ validated, enriched call
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Skills Layer  —  skills/*.py                                        │
│  Each skill has name + description + input/output JSON schemas and   │
│  an async invoke(args, ctx) -> SkillResult. Decoupled from the LLM.  │
└──────────────────────────────────────────────────────────────────────┘
```

Responsibilities are strict:

The **agent** picks tools and sequences reasoning steps. It never embeds business logic. Swapping the agent framework (LangGraph, custom ReAct loop) doesn't require touching any skill.

**Skills** carry business capabilities — "look up a company", "create an opportunity", "draft a proposal deck". They are pure async functions with typed envelopes (`SkillResult`). They know nothing about prompts or the LLM.

The **MCP-style registry** is the contract between the two. It holds specs, exposes a JSON-schema manifest, and knows how to invoke a skill by name. An `mcp/server.py` facade accepts MCP-shaped requests (`tools/list`, `tools/call`) so the same skills can be exposed to external MCP clients without a rewrite.

**Hooks** are cross-cutting middleware around every tool call. They run in a defined order (pre → handler → post, with error as a side channel) and individual hooks can be added or removed without touching skills.

**Observability** (`observability/logging.py`) installs a JSON formatter on the root logger so every log line — including the per-invocation audit records emitted by `AuditLogHook` — is machine-readable and ready for aggregation.

## How It Works (end-to-end flow)

A single user turn traces cleanly through every layer.

1. **Transport.** `bot/bot.py` receives a Bot Framework activity, pulls out `session_id` and user text, and calls `SalesAgent.run(text, session_id)`.
2. **Agent.** `SalesAgent` builds a per-request `AgentExecutor` with tools adapted from the registry (`registry.to_langchain_tools`). The LLM sees the system prompt, the conversation history (from Redis if configured, else in-process), and the structured tool list. It decides which tool to call.
3. **Registry.** The LangChain `StructuredTool` wrapper calls back into `ToolRegistry.invoke(name, arguments, ctx)`. `ctx` is freshly minted per invocation and carries `session_id` and a `correlation_id`.
4. **Hooks — pre.** `JSONSchemaValidationHook` validates arguments against the skill's `input_schema`. `SessionEnrichmentHook` fills missing common fields (like `user_message`) from context metadata.
5. **Skill.** The skill runs its async `invoke` and returns a `SkillResult(success, output, error, metadata)`.
6. **Hooks — post.** `AuditLogHook` emits a structured JSON record (`tool`, `session_id`, `correlation_id`, `success`, `duration_ms`, arg keys, error if any). `MetricsHook` updates in-memory counters and latency samples.
7. **Hooks — error (only if raised).** `RetryAndFallbackHook` retries a small number of times on transient errors and otherwise converts the exception into a graceful `SkillResult(success=False, error=...)` so the agent can still produce a reply.
8. **Agent response.** The agent synthesizes a natural-language reply from the tool output(s) and returns it to `bot.py`, which sends it back to the user.

A `/agent/tools` HTTP endpoint exposes the same manifest the agent sees — handy for debugging and for introspection from external MCP clients.

## Agentic Capabilities

**Dynamic tool selection.** The agent picks which skill to call based on the JSON-schema-backed descriptions in the registry. There is no hardcoded `intent → function` dispatch anywhere in the code. Adding a new skill is enough to make it available to the agent.

**Multi-step reasoning.** `create_openai_tools_agent` + `AgentExecutor` allow the agent to call several tools in sequence within one user turn — e.g. `get_past_projects` followed by `draft_proposal` when the user asks "draft a follow-up deck for Acme based on what we've done before".

**Context awareness.** Conversation history is persisted in Redis (falling back to in-process if `REDIS_URL` is unset), and the opportunity skill additionally maintains partial-field state across turns so it can gather all required CRM fields over multiple messages.

**Structured invocation & discovery.** Every tool has an input/output JSON schema. The `mcp/server.py` facade speaks `tools/list` and `tools/call` — the same two methods any MCP client uses — so the skill set is portable.

## Extending the System — Adding a New Skill

1. Create `skills/my_skill.py` with a subclass of `Skill`:

   ```python
   from typing import Any, Dict
   from skills.base import Skill, SkillContext, SkillResult

   class GetQuoteSkill(Skill):
       name = "get_quote"
       description = "Produce a price quote for a given product and quantity."
       input_schema = {
           "type": "object",
           "properties": {
               "product": {"type": "string"},
               "quantity": {"type": "integer"},
           },
           "required": ["product", "quantity"],
           "additionalProperties": False,
       }
       output_schema = {"type": "object"}

       async def invoke(self, arguments: Dict[str, Any], ctx: SkillContext) -> SkillResult:
           price = _calc_price(arguments["product"], arguments["quantity"])
           return SkillResult(success=True, output={"price_usd": price})
   ```

2. Register it in `agent/sales_agent.py::build_registry`:

   ```python
   registry.register(GetQuoteSkill(), tags=["pricing"])
   ```

3. Write a test in `tests/test_skills.py`. Done — the agent discovers it automatically, validation + logging + metrics + retry come for free, and external MCP clients can call it through `mcp/server.py`.

## Hooks & Observability

Hooks live in `hooks/` and are composed by `HookManager`:

```python
HookManager(
    pre=[JSONSchemaValidationHook(), SessionEnrichmentHook()],
    post=[AuditLogHook(), MetricsHook()],
    error=[RetryAndFallbackHook(max_retries=1)],
)
```

Each phase has a contract: pre-hooks may transform arguments, post-hooks observe results, error-hooks may produce a fallback `SkillResult`. Any concern (rate limiting, PII redaction, tenant scoping) can be added as another hook without touching skills or the agent.

`AuditLogHook` emits one structured JSON line per tool invocation:

```json
{
  "event": "tool_invocation",
  "tool": "get_company_info",
  "session_id": "conv-42",
  "correlation_id": "a6c2…",
  "success": true,
  "duration_ms": 184.7,
  "arg_keys": ["user_message"]
}
```

Argument values are omitted by default to avoid leaking PII; pass `AuditLogHook(log_argument_values=True)` in non-production environments when you need them.

`MetricsHook.snapshot()` returns per-tool success/failure counts and average/max latency for lightweight in-process metrics. Swap it for Prometheus/OTLP when you're ready — the hook interface doesn't change.

`configure_logging()` (in `observability/logging.py`) installs a JSON formatter on the root logger so every log record — application and audit alike — ships as structured JSON.

## Project Layout

```
agent/            Agent layer (LangChain AgentExecutor, registry binding)
skills/           Reusable business capabilities with JSON schemas
  base.py         Skill ABC, SkillContext, SkillResult
  greeting.py, farewell.py, thanks.py, fallback.py
  company_info.py, past_projects.py
  create_opportunity.py, draft_proposal.py
mcp/              MCP-style tool registry and request facade
  registry.py     Registration, discovery, invocation, LangChain adapter
  server.py       tools/list + tools/call handler
hooks/            Pre/post/error middleware
  base.py, validation.py, enrichment.py
  logging_hook.py, metrics.py, error_hook.py
observability/    Structured JSON logging
bot/              Microsoft Bot Framework adapter (thin transport shell)
handlers/         LLM-backed business logic, wrapped by skills
config/           Environment config (OPENAI_API_KEY, REDIS_URL, …)
utils/            Small helpers (JSON loader, response parser)
tests/            Pytest suite for registry, hooks, and skills
langchain_setup/  Compatibility shim for the legacy agent entrypoint
commands/         Legacy intent-command wrappers (no longer wired in)
main.py           FastAPI entrypoint: boots agent, exposes /bot and /agent/tools
```

## Technical Stack

### Language & Runtime

Python 3.9+ with full async/await throughout the agent, registry, hooks, and skills. Type hints (`typing`, `dataclasses`) are used across every layer to keep the contracts between components explicit.

### Agent & LLM

| Component | Library | Role |
|---|---|---|
| Agent executor | `langchain` / `langchain-classic` | Hosts the OpenAI tool-calling loop (`create_openai_tools_agent` + `AgentExecutor`). Imported with a version-resilient fallback so either LangChain 0.x or 1.2+ works. |
| LLM provider | `langchain-openai` | Wraps GPT-4 (`gpt-4o`) via `ChatOpenAI`. |
| Core primitives | `langchain-core` | `ChatPromptTemplate`, `MessagesPlaceholder`, `InMemoryChatMessageHistory`. |
| Community integrations | `langchain-community` | `RedisChatMessageHistory` for persisted chat memory. |

### Tool Registry (MCP-style)

A lightweight in-process `ToolRegistry` (`mcp/registry.py`) owns skill registration, discovery (JSON-schema manifest), and structured invocation. `mcp/server.py` adds an MCP-shaped request facade that speaks `tools/list` and `tools/call` so the registry can be fronted by a real MCP transport later without changing skills.

### Skills & Validation

| Component | Library | Role |
|---|---|---|
| Skill contracts | stdlib (`abc`, `dataclasses`) | `Skill` ABC, `SkillContext`, `SkillResult` envelope — zero framework lock-in. |
| Schema validation | `jsonschema` (Draft 2020-12) | Enforces skill input schemas in the pre-hook pipeline; degrades gracefully if the library is missing. |
| Structured tool args | `pydantic` | LangChain `StructuredTool` arg models derived from each skill's JSON schema. |

### Hooks & Observability

| Component | Library | Role |
|---|---|---|
| Hook manager | stdlib | Composes pre / post / error middleware around every tool invocation. |
| Structured logging | stdlib `logging` + custom JSON formatter | `observability/logging.py` emits one JSON line per record; audit records from `AuditLogHook` merge as first-class structured events. |
| Metrics | in-process | `MetricsHook.snapshot()` exposes per-tool counters and latency; designed to be swapped for Prometheus / OTLP without changing the hook interface. |
| Resilience | stdlib `asyncio` | `RetryAndFallbackHook` provides bounded retry on transient failures and converts unrecoverable errors into a graceful `SkillResult`. |

### Transport & HTTP

| Component | Library | Role |
|---|---|---|
| Web framework | `fastapi` | Hosts `/bot` (Bot Framework webhook), `/` (health check), `/agent/tools` (MCP manifest). |
| ASGI server | `uvicorn` / `gunicorn` | Local dev and production serving. |
| Channel adapters | `botbuilder-core`, `botbuilder-schema` | Microsoft Bot Framework integration for Teams and Telegram. |
| HTTP client | `aiohttp` | Transitive async HTTP used by the bot framework. |

### Content Generation & Storage

| Component | Library | Role |
|---|---|---|
| PowerPoint generation | `python-pptx` | Renders proposal decks from LLM-generated outlines. |
| Blob storage | `azure-storage-blob` | Hosts generated `.pptx` files; the skill returns a public attachment URL. |
| Conversation memory | `redis` (optional) | Persists chat history per session; in-process fallback (`InMemoryChatMessageHistory`) activates when `REDIS_URL` is empty. |

### Configuration

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | yes | Authenticates the LLM client. |
| `REDIS_URL` | no | Enables persistent chat memory; omit for in-process memory. |
| `MICROSOFT_APP_ID` | for Teams/Telegram | Bot Framework app id. |
| `MICROSOFT_APP_PASSWORD` | for Teams/Telegram | Bot Framework app password. |
| `BLOB_CONNECTION_STR` | for proposal skill | Azure Blob Storage connection string. |
| `CONTAINER_NAME` | no (defaults `salesbotdrafts`) | Blob container for generated decks. |

Environment loading uses `python-dotenv` for local development.

### Testing & Tooling

| Component | Library | Role |
|---|---|---|
| Test runner | `pytest` | Executes the suite under `tests/`. |
| Async tests | `pytest-asyncio` | Lets the suite `await` skills, hooks, and the registry directly. |

Fifteen tests cover the registry, the MCP facade, every hook phase, and the skills that don't require the LLM. Run with `pytest -q`.

### Deployment Target

Infrastructure targets Azure: Azure Bot Service hosts the channel registrations, Azure Web App runs the FastAPI process, Azure Blob Storage stores generated decks, and a managed Redis (free tier is fine for light use) stores conversation history. CI is wired through `.github/workflows/main_essalesagent.yml`.

## Running Locally

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-…
# REDIS_URL is optional — omit it to use in-process memory.

# Interactive REPL
python main.py

# Or serve the full FastAPI app
uvicorn main:app --host 0.0.0.0 --port 8000
```

Run the tests:

```bash
pytest -q
```

Inspect the live tool manifest once the server is up:

```bash
curl http://localhost:8000/agent/tools
```

## Example Flow

**User input:** *"Can you draft a proposal for Acme based on what we've done with them?"*

1. `MyBot.on_message_activity` → `SalesAgent.run(text, session_id)`.
2. LLM (via `AgentExecutor`) picks `get_past_projects` with `{"company_name": "Acme"}`.
3. `ToolRegistry.invoke("get_past_projects", …)` runs the hook pipeline:
   * `JSONSchemaValidationHook` confirms `company_name` is present.
   * `PastProjectsSkill.invoke` returns `SkillResult(success=True, output={...})`.
   * `AuditLogHook` logs `{"event":"tool_invocation","tool":"get_past_projects",…}`.
   * `MetricsHook` increments the success counter.
4. LLM now picks `draft_proposal` with a composed `user_message` that includes the Acme history.
5. Second invocation goes through the same hook pipeline; `DraftProposalSkill` generates the deck, uploads it to blob storage, and returns `{ text, attachment_url }`.
6. `AgentExecutor` synthesizes: *"Here's a draft proposal for Acme that builds on the AI pilot we did with Jane last year — attachment link: …"*.
7. `MyBot` sends the message back through the Bot Framework adapter.

Every step is visible in the audit log; the whole turn is a deterministic, inspectable sequence of tool calls.

"""The agentic core.

`SalesAgent` wires together:
  * a `ToolRegistry` populated with skills,
  * a `HookManager` with validation/enrichment/logging/metrics/error hooks,
  * a LangChain `AgentExecutor` that lets the LLM dynamically select and
    call any registered skill.

The agent is created once at boot and re-used per request. Per-request
concerns (session id, correlation id) live in `SkillContext`, produced by
`ctx_factory` on every tool call.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

# Import path differs across LangChain versions:
#   * langchain < 1.2 exposes these at langchain.agents
#   * langchain >= 1.2 relocates them to langchain_classic.agents
try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent  # type: ignore
except ImportError:  # pragma: no cover - only runs on langchain >= 1.2
    from langchain_classic.agents import (  # type: ignore
        AgentExecutor,
        create_openai_tools_agent,
    )

try:
    from langchain.memory import ConversationBufferMemory  # type: ignore
except ImportError:  # pragma: no cover
    from langchain_classic.memory import ConversationBufferMemory  # type: ignore

from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config.settings import REDIS_URL
from hooks import (
    AuditLogHook,
    HookManager,
    JSONSchemaValidationHook,
    MetricsHook,
    RetryAndFallbackHook,
    SessionEnrichmentHook,
)
from mcp.registry import ToolRegistry
from observability.logging import get_logger
from skills.base import SkillContext
from skills.company_info import CompanyInfoSkill
from skills.create_opportunity import CreateOpportunitySkill
from skills.draft_proposal import DraftProposalSkill
from skills.farewell import FarewellSkill
from skills.fallback import FallbackSkill
from skills.greeting import GreetingSkill
from skills.past_projects import PastProjectsSkill
from skills.thanks import ThanksSkill

_LOG = get_logger("essales.agent")


SYSTEM_PROMPT = (
    "You are Jordan, an agentic AI sales assistant. You orchestrate "
    "specialized tools (skills) to help sales agents. Principles:\n"
    "  * Always prefer calling a skill over answering from memory when the "
    "task maps to one.\n"
    "  * Only call `fallback_response` as a last resort for out-of-scope "
    "questions.\n"
    "  * When creating an opportunity, pass the full user message to "
    "`create_opportunity` - it handles field extraction and multi-turn "
    "collection itself.\n"
    "  * When looking up company info, use `get_company_info` for profiles "
    "and `get_past_projects` for prior engagement history.\n"
    "  * Summarize tool outputs for the user in plain language; do not "
    "echo raw JSON unless asked."
)


def build_hook_manager(metrics: Optional[MetricsHook] = None) -> HookManager:
    """Standard hook pipeline used in production."""
    return HookManager(
        pre=[JSONSchemaValidationHook(), SessionEnrichmentHook()],
        post=[AuditLogHook(), metrics or MetricsHook()],
        error=[RetryAndFallbackHook(max_retries=1)],
    )


def build_registry(
    *,
    opportunity_handler: Any,
    company_handler: Any,
    proposal_handler: Any,
    hook_manager: Optional[HookManager] = None,
) -> ToolRegistry:
    """Build and populate the registry with all production skills."""
    registry = ToolRegistry(hook_manager=hook_manager or build_hook_manager())

    registry.register(GreetingSkill(), tags=["conversation"])
    registry.register(FarewellSkill(), tags=["conversation"])
    registry.register(ThanksSkill(), tags=["conversation"])
    registry.register(FallbackSkill(), tags=["conversation"])
    registry.register(
        CompanyInfoSkill(company_handler=company_handler), tags=["research"]
    )
    registry.register(PastProjectsSkill(), tags=["research"])
    registry.register(
        CreateOpportunitySkill(opportunity_handler=opportunity_handler),
        tags=["crm"],
    )
    registry.register(
        DraftProposalSkill(proposal_handler=proposal_handler),
        tags=["content"],
    )

    _LOG.info(
        '{"event":"registry_ready","tools":%s}',
        [s.name for s in registry.list_tools()],
    )
    return registry


def _get_chat_memory(session_id: str) -> ConversationBufferMemory:
    """Redis-backed memory when configured, else in-process."""
    if REDIS_URL:
        history = RedisChatMessageHistory(session_id=session_id, url=REDIS_URL)
    else:
        history = InMemoryChatMessageHistory()
    return ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=history,
        return_messages=True,
    )


class SalesAgent:
    """High-level facade: `await agent.run(user_input, session_id)`."""

    def __init__(self, llm: Any, registry: ToolRegistry):
        self._llm = llm
        self._registry = registry

    def _make_ctx_factory(self, session_id: str, user_message: str):
        def _factory() -> SkillContext:
            return SkillContext(
                session_id=session_id,
                correlation_id=str(uuid.uuid4()),
                metadata={"original_user_message": user_message},
            )

        return _factory

    def _build_executor(
        self, session_id: str, user_message: str
    ) -> AgentExecutor:
        tools = self._registry.to_langchain_tools(
            self._make_ctx_factory(session_id, user_message)
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )
        agent = create_openai_tools_agent(self._llm, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            memory=_get_chat_memory(session_id),
            handle_parsing_errors=True,
            verbose=False,
        )

    async def run(self, user_input: str, session_id: str) -> str:
        _LOG.info(
            '{"event":"user_turn","session_id":"%s","input_len":%s}',
            session_id,
            len(user_input or ""),
        )
        executor = self._build_executor(session_id, user_input)
        raw = await executor.ainvoke({"input": user_input})
        if isinstance(raw, dict) and "output" in raw:
            return raw["output"]
        return str(raw)

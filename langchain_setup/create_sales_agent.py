"""Legacy compatibility shim.

The old entrypoint built a LangChain `AgentExecutor` with hardcoded
`Tool` wrappers over the `commands/` modules. That responsibility now
lives in `agent.sales_agent.SalesAgent`, which consults the MCP-style
`ToolRegistry` instead of hardcoding the tool list.

This shim stays in place so that any caller still importing the old
function keeps working while they migrate. It builds a registry + agent
on the fly and returns an object with an `ainvoke({"input": ...})`
method that mirrors the original surface.
"""

from __future__ import annotations

from typing import Any

from agent import SalesAgent, build_registry


class _AgentExecutorCompat:
    """Matches the minimal `AgentExecutor.ainvoke` surface used by callers."""

    def __init__(self, agent: SalesAgent, session_id: str):
        self._agent = agent
        self._session_id = session_id

    async def ainvoke(self, payload: dict) -> dict:
        user_input = payload.get("input", "")
        output = await self._agent.run(user_input, self._session_id)
        return {"output": output}


async def create_sales_assistant_agent(
    llm: Any,
    opportunity_handler: Any,
    company_handler: Any,
    proposal_handler: Any,
    session_id: str,
):
    """DEPRECATED. Use `agent.SalesAgent` + `agent.build_registry` directly."""
    registry = build_registry(
        opportunity_handler=opportunity_handler,
        company_handler=company_handler,
        proposal_handler=proposal_handler,
    )
    agent = SalesAgent(llm=llm, registry=registry)
    return _AgentExecutorCompat(agent, session_id)

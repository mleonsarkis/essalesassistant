"""Agent layer: orchestrates reasoning and delegates execution to skills
via the MCP-style registry. The agent does *not* know about business
logic — its only job is to choose the right tool, pass well-formed
arguments, and synthesize a response.
"""

from agent.sales_agent import SalesAgent, build_registry, build_hook_manager

__all__ = ["SalesAgent", "build_registry", "build_hook_manager"]

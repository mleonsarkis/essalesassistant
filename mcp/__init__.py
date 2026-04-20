"""MCP-style tool registry.

This package implements an in-process, MCP-inspired tool registry so that
skills are discoverable, have structured inputs/outputs, and can be re-used
across agents and services. A thin `server` facade additionally speaks an
MCP-compatible request/response shape (`tools/list` and `tools/call`) so the
same skills can be exposed to external MCP clients without a rewrite.
"""

from mcp.registry import ToolRegistry, ToolSpec

__all__ = ["ToolRegistry", "ToolSpec"]

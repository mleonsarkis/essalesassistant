"""MCP-style request facade.

Exposes the same `ToolRegistry` over an MCP-compatible request/response
envelope. This is *not* a full MCP server (no JSON-RPC framing / transport),
but a pure function that external services can wrap in any transport —
HTTP handler, stdio JSON-RPC, or even a test harness.

Supported methods:
  * `tools/list` -> { "tools": [...] }
  * `tools/call` -> { "content": [{ "type": "text", "text": "..." }],
                     "isError": bool }

This is intentionally minimal but schema-compatible with the MCP spec's
shape for those two methods, so a thin adapter can promote it to a real
MCP server later.
"""

from __future__ import annotations

from typing import Any, Dict

from mcp.registry import ToolRegistry
from skills.base import SkillContext


async def handle_mcp_request(
    payload: Dict[str, Any],
    registry: ToolRegistry,
    ctx: SkillContext,
) -> Dict[str, Any]:
    method = payload.get("method")
    params = payload.get("params") or {}

    if method == "tools/list":
        return registry.get_manifest()

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not name:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Missing 'name' in params."}],
            }
        result = await registry.invoke(name, arguments, ctx)
        return {
            "isError": not result.success,
            "content": [
                {
                    "type": "text",
                    "text": (result.output if result.success else result.error)
                    if isinstance(result.output, str) or not result.success
                    else __import__("json").dumps(result.output, default=str),
                }
            ],
        }

    return {
        "isError": True,
        "content": [
            {"type": "text", "text": f"Unknown method: {method!r}"}
        ],
    }

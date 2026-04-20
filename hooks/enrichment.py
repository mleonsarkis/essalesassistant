"""Pre-hook: fill in fields that skills commonly expect but agents sometimes omit."""

from __future__ import annotations

from typing import Any, Dict

from hooks.base import Hook
from mcp.registry import ToolSpec
from skills.base import SkillContext


class SessionEnrichmentHook(Hook):
    """Ensure `user_message` is populated from context metadata when missing.

    The agent usually provides it, but this keeps skills robust to slightly
    malformed tool calls without each skill having to re-implement the check.
    """

    async def pre(
        self, spec: ToolSpec, arguments: Dict[str, Any], ctx: SkillContext
    ) -> Dict[str, Any]:
        if "user_message" in spec.input_schema.get("properties", {}):
            if not arguments.get("user_message"):
                fallback = ctx.metadata.get("original_user_message")
                if fallback:
                    arguments["user_message"] = fallback
        return arguments

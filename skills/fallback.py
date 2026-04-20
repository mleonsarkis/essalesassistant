"""Fallback skill — final safety net for out-of-scope queries."""

from __future__ import annotations

from typing import Any, Dict

from skills.base import Skill, SkillContext, SkillResult


class FallbackSkill(Skill):
    name = "fallback_response"
    description = (
        "Use ONLY as a last resort when no other skill applies and the user's "
        "request is clearly outside sales assistant scope (weather, cooking, "
        "general trivia, etc.). Do not use if any other skill could plausibly fit."
    )
    input_schema = {
        "type": "object",
        "properties": {"user_message": {"type": "string"}},
        "required": [],
        "additionalProperties": False,
    }
    output_schema = {"type": "string"}

    async def invoke(
        self, arguments: Dict[str, Any], ctx: SkillContext
    ) -> SkillResult:
        return SkillResult(
            success=True,
            output="Sorry, I'm a sales assistant and can't help with that.",
        )

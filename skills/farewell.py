"""Farewell skill — graceful conversation close."""

from __future__ import annotations

from typing import Any, Dict

from skills.base import Skill, SkillContext, SkillResult


class FarewellSkill(Skill):
    name = "say_goodbye"
    description = (
        "Use when the user signals the conversation is ending "
        "('bye', 'thanks that's all', 'talk later')."
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
            output="Goodbye! Feel free to reach out anytime.",
        )

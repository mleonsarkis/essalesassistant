"""Thanks skill — acknowledge user gratitude."""

from __future__ import annotations

from typing import Any, Dict

from skills.base import Skill, SkillContext, SkillResult


class ThanksSkill(Skill):
    name = "acknowledge_thanks"
    description = "Use when the user expresses gratitude ('thanks', 'appreciate it')."
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
            output="You're welcome! Let me know if you need anything else.",
        )

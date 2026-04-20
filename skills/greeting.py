"""Greeting skill — first-touch conversational response."""

from __future__ import annotations

from typing import Any, Dict

from skills.base import Skill, SkillContext, SkillResult


class GreetingSkill(Skill):
    name = "greet_user"
    description = (
        "Respond to greetings or openers like 'hi', 'hello', 'hey Jordan'. "
        "Use this exclusively for social openers, not for any business task."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "user_message": {
                "type": "string",
                "description": "The original user message that triggered the greeting.",
            }
        },
        "required": [],
        "additionalProperties": False,
    }
    output_schema = {"type": "string"}

    async def invoke(
        self, arguments: Dict[str, Any], ctx: SkillContext
    ) -> SkillResult:
        return SkillResult(
            success=True,
            output=(
                "Hello! I'm Jordan, an agentic sales assistant. "
                "I can look up company info, surface past projects, "
                "create opportunities in HubSpot, and draft proposal decks."
            ),
        )

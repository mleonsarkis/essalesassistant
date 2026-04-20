"""Company info skill — wraps the existing CompanyHandler.

This is a good example of how the skills layer decouples business logic:
the skill carries the schema and metadata the agent needs, while delegating
actual LLM-backed work to `CompanyHandler`. Either side can evolve
independently — swap the backend to a vector DB later, or expose this same
skill to a different agent, without touching the agent's prompt.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from skills.base import Skill, SkillContext, SkillResult


class CompanyInfoSkill(Skill):
    name = "get_company_info"
    description = (
        "Look up a detailed profile for a company (industry, size, location, "
        "revenue, recent news). Use whenever the user asks ABOUT a company "
        "as the primary subject. Do NOT use when the company is mentioned "
        "only as a field of another task (e.g. creating an opportunity)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "user_message": {
                "type": "string",
                "description": "The user's original question about the company.",
            },
            "company_name": {
                "type": "string",
                "description": "Optional explicit company name; extracted from the message if omitted.",
            },
        },
        "required": ["user_message"],
        "additionalProperties": False,
    }
    output_schema = {"type": "string"}

    def __init__(self, company_handler: Any):
        self.company_handler = company_handler

    async def invoke(
        self, arguments: Dict[str, Any], ctx: SkillContext
    ) -> SkillResult:
        user_message: str = arguments["user_message"]
        try:
            reply = await self.company_handler.handle(user_message, ctx.session_id)
            return SkillResult(success=True, output=reply)
        except Exception as exc:  # noqa: BLE001 — bubble up structured error
            return SkillResult(
                success=False,
                error=f"CompanyInfo lookup failed: {exc}",
            )

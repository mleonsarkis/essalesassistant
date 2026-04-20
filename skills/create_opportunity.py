"""Create-opportunity skill — wraps the existing OpportunityHandler."""

from __future__ import annotations

from typing import Any, Dict

from skills.base import Skill, SkillContext, SkillResult


class CreateOpportunitySkill(Skill):
    name = "create_opportunity"
    description = (
        "Create a sales opportunity in the CRM. Use this ONLY when the user "
        "expresses intent to create/log/add an opportunity. The skill will "
        "extract the five required CRM fields (contact_name, company_name, "
        "deal_stage, amount, close_date) and persist partial state across "
        "turns until all fields are collected."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "user_message": {
                "type": "string",
                "description": "Full user message containing partial or complete opportunity details.",
            }
        },
        "required": ["user_message"],
        "additionalProperties": False,
    }
    output_schema = {"type": "string"}

    def __init__(self, opportunity_handler: Any):
        self.opportunity_handler = opportunity_handler

    async def invoke(
        self, arguments: Dict[str, Any], ctx: SkillContext
    ) -> SkillResult:
        user_message: str = arguments["user_message"]
        try:
            reply = await self.opportunity_handler.handle(user_message, ctx.session_id)
            return SkillResult(success=True, output=reply)
        except Exception as exc:  # noqa: BLE001
            return SkillResult(
                success=False,
                error=f"Opportunity creation failed: {exc}",
            )

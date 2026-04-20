"""Draft-proposal skill — wraps the existing ProposalHandler."""

from __future__ import annotations

from typing import Any, Dict

from skills.base import Skill, SkillContext, SkillResult


class DraftProposalSkill(Skill):
    name = "draft_proposal"
    description = (
        "Generate a project proposal outline and a PowerPoint deck based on "
        "user-provided context. Use when the user asks to draft, create, or "
        "prepare a proposal / presentation / pitch deck."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "user_message": {
                "type": "string",
                "description": "User's description of the proposal to draft.",
            }
        },
        "required": ["user_message"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "attachment_url": {"type": "string"},
        },
    }

    def __init__(self, proposal_handler: Any):
        self.proposal_handler = proposal_handler

    async def invoke(
        self, arguments: Dict[str, Any], ctx: SkillContext
    ) -> SkillResult:
        user_message: str = arguments["user_message"]
        try:
            # `ProposalHandler.handle` returns a Bot Framework Activity; we pull
            # the parts a caller typically needs without leaking that type.
            activity = await self.proposal_handler.handle(user_message)
            text = getattr(activity, "text", "Proposal drafted.")
            attachment_url = None
            attachments = getattr(activity, "attachments", None) or []
            if attachments:
                attachment_url = getattr(attachments[0], "content_url", None)
            return SkillResult(
                success=True,
                output={"text": text, "attachment_url": attachment_url},
                metadata={"activity": activity},
            )
        except Exception as exc:  # noqa: BLE001
            return SkillResult(
                success=False,
                error=f"Proposal drafting failed: {exc}",
            )

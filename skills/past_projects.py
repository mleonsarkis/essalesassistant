"""Past projects skill — returns prior engagements from the known-companies dataset.

Split out from `get_company_info` because the agent should be able to
surface past-project context even when the user hasn't asked for a full
company profile (e.g. "have we worked with Acme before?").
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from skills.base import Skill, SkillContext, SkillResult
from utils.loader import load_json


class PastProjectsSkill(Skill):
    name = "get_past_projects"
    description = (
        "Return prior project history and internal contacts for a company from "
        "the known-companies knowledge base. Use when the user asks about "
        "previous engagements, internal owners, or historical work with a client."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "Company name to look up (case-insensitive).",
            }
        },
        "required": ["company_name"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "project_details": {"type": "string"},
            "worked_with": {"type": "string"},
            "contacts": {"type": "array", "items": {"type": "string"}},
        },
    }

    def __init__(self, data_path: str = "data/known_companies.json"):
        self._data_path = data_path
        self._cache: Optional[List[Dict[str, Any]]] = None

    def _load(self) -> List[Dict[str, Any]]:
        if self._cache is None:
            self._cache = load_json(self._data_path)
        return self._cache

    async def invoke(
        self, arguments: Dict[str, Any], ctx: SkillContext
    ) -> SkillResult:
        target = arguments["company_name"].strip().lower()
        try:
            match = next(
                (
                    c
                    for c in self._load()
                    if c.get("company_name", "").lower() == target
                ),
                None,
            )
        except Exception as exc:  # noqa: BLE001
            return SkillResult(success=False, error=f"Knowledge base read failed: {exc}")

        if not match:
            return SkillResult(
                success=True,
                output=f"No prior project history found for {arguments['company_name']}.",
                metadata={"found": False},
            )

        return SkillResult(
            success=True,
            output={
                "company_name": match["company_name"],
                "project_details": match.get("project_details", ""),
                "worked_with": match.get("worked_with", ""),
                "contacts": match.get("contacts", []),
            },
            metadata={"found": True},
        )

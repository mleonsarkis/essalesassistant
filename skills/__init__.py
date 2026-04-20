"""Skills layer: reusable business capabilities exposed through the tool registry.

Each skill is a self-contained unit with:
  * a name and description (used by the agent to pick the right tool)
  * input/output JSON schemas (used for validation and documentation)
  * an async `invoke(arguments, ctx) -> SkillResult` method

Skills are registered into the MCP-style `ToolRegistry`, which the agent
consults at runtime instead of relying on hardcoded intent -> function routing.
"""

from skills.base import Skill, SkillContext, SkillResult

__all__ = ["Skill", "SkillContext", "SkillResult"]

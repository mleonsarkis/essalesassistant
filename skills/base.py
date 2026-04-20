"""Base contracts for the Skills layer.

A Skill is a self-contained capability that the agent can invoke. Skills are
intentionally decoupled from the agent: they do not know about prompts, the
LLM, or conversation state beyond what's passed to them via `SkillContext`.
This separation lets skills be unit-tested in isolation and reused across
multiple agents or direct API calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SkillContext:
    """Runtime context threaded through every skill invocation.

    Carries identifiers and cross-cutting concerns (session id, correlation
    id, caller identity) without polluting the skill's input schema.
    """

    session_id: str = "default"
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Uniform return envelope for all skills.

    Using a typed envelope lets hooks (logging, metrics, error handling)
    reason about outcomes without caring about the concrete payload shape.
    """

    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Convenient access for LangChain Tool wrappers, which expect a string.
    def as_text(self) -> str:
        if self.success:
            return str(self.output) if self.output is not None else ""
        return self.error or "Unknown error"


class Skill(ABC):
    """Abstract base class for all skills.

    Subclasses declare metadata (name, description, schemas) as class
    attributes and implement the async `invoke` method.
    """

    #: Unique identifier used by the agent to reference this skill.
    name: str = ""

    #: Natural-language description the agent uses to decide *when* to call it.
    description: str = ""

    #: JSON Schema describing the shape of the `arguments` dict passed to `invoke`.
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }

    #: JSON Schema describing the `output` field of `SkillResult` on success.
    output_schema: Dict[str, Any] = {"type": "string"}

    @abstractmethod
    async def invoke(
        self, arguments: Dict[str, Any], ctx: SkillContext
    ) -> SkillResult:
        """Execute the skill. Must be async. Must not raise on expected errors —
        return `SkillResult(success=False, error=...)` instead. Hooks handle
        unexpected exceptions centrally.
        """
        raise NotImplementedError

    def spec(self) -> Dict[str, Any]:
        """Machine-readable spec exported to the registry and MCP manifest."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }

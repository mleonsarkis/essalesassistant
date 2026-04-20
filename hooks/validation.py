"""Pre-hook: validate skill arguments against the skill's JSON schema.

Uses `jsonschema` if available; degrades gracefully to a best-effort
required-key check if the library isn't installed, so the system keeps
working on minimal installs.
"""

from __future__ import annotations

from typing import Any, Dict

from hooks.base import Hook
from mcp.registry import ToolSpec
from skills.base import SkillContext

try:
    from jsonschema import Draft202012Validator, ValidationError  # type: ignore
    _HAS_JSONSCHEMA = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_JSONSCHEMA = False


class JSONSchemaValidationHook(Hook):
    """Raise ValueError if the provided arguments don't match the skill schema."""

    async def pre(
        self, spec: ToolSpec, arguments: Dict[str, Any], ctx: SkillContext
    ) -> Dict[str, Any]:
        if _HAS_JSONSCHEMA:
            validator = Draft202012Validator(spec.input_schema)
            errors = sorted(validator.iter_errors(arguments), key=lambda e: e.path)
            if errors:
                details = "; ".join(
                    f"{list(e.path) or '<root>'}: {e.message}" for e in errors
                )
                raise ValueError(f"Invalid arguments for '{spec.name}': {details}")
        else:
            required = spec.input_schema.get("required", []) or []
            missing = [r for r in required if r not in arguments]
            if missing:
                raise ValueError(
                    f"Invalid arguments for '{spec.name}': missing {missing}"
                )
        return arguments

"""In-process tool registry with MCP-style structured invocation.

Responsibilities:
  * Hold the canonical list of registered skills (tool specs).
  * Invoke a skill by name, with arguments validated against its input
    schema and with the hook pipeline applied automatically.
  * Expose discovery APIs (`list_tools`, `get_manifest`) so the agent —
    and future external MCP clients — can learn what's available.
  * Adapt skills into LangChain `Tool` instances for the agent layer.

The registry is deliberately the only place that knows how to *invoke* a
skill. Hooks live outside skills; skills stay pure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from skills.base import Skill, SkillContext, SkillResult


@dataclass
class ToolSpec:
    """Registry entry for a single skill."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    skill: Skill
    tags: List[str] = field(default_factory=list)


class ToolRegistry:
    """Registry + structured invoker for skills."""

    def __init__(self, hook_manager: Optional["HookManager"] = None):  # noqa: F821
        # Avoid a hard import cycle with hooks/
        self._tools: Dict[str, ToolSpec] = {}
        self._hook_manager = hook_manager

    # -- registration / discovery -------------------------------------------------

    def register(self, skill: Skill, *, tags: Optional[List[str]] = None) -> ToolSpec:
        if not skill.name:
            raise ValueError(f"Skill {skill!r} must declare a non-empty name")
        if skill.name in self._tools:
            raise ValueError(f"Tool '{skill.name}' already registered")
        spec = ToolSpec(
            name=skill.name,
            description=skill.description,
            input_schema=skill.input_schema,
            output_schema=skill.output_schema,
            skill=skill,
            tags=list(tags or []),
        )
        self._tools[skill.name] = spec
        return spec

    def list_tools(self) -> List[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def get_manifest(self) -> Dict[str, Any]:
        """MCP-style manifest of available tools (JSON-serializable)."""
        return {
            "tools": [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "inputSchema": spec.input_schema,
                    "outputSchema": spec.output_schema,
                    "tags": spec.tags,
                }
                for spec in self._tools.values()
            ]
        }

    # -- invocation ---------------------------------------------------------------

    async def invoke(
        self,
        name: str,
        arguments: Dict[str, Any],
        ctx: SkillContext,
    ) -> SkillResult:
        """Invoke a tool by name with hook pipeline applied."""
        spec = self.get(name)

        async def _run(args: Dict[str, Any]) -> SkillResult:
            return await spec.skill.invoke(args, ctx)

        if self._hook_manager is None:
            return await _run(arguments)
        return await self._hook_manager.run(spec, arguments, ctx, _run)

    # -- LangChain adapter --------------------------------------------------------

    def to_langchain_tools(
        self, ctx_factory: Callable[[], SkillContext]
    ) -> List[Any]:
        """Adapt each registered skill into a LangChain `StructuredTool`.

        `ctx_factory` is a zero-arg callable because a fresh `SkillContext`
        may need to be produced per invocation (e.g. a new correlation id).
        """
        # Local import keeps core registry importable without LangChain.
        from langchain.tools import StructuredTool
        from pydantic import create_model, Field

        tools: List[Any] = []
        for spec in self._tools.values():
            args_model = _pydantic_model_from_schema(spec.name, spec.input_schema)

            async def _coro(
                __spec_name: str = spec.name,
                **kwargs: Any,
            ) -> str:
                result = await self.invoke(__spec_name, kwargs, ctx_factory())
                return _result_to_tool_text(result)

            def _sync(__spec_name: str = spec.name, **kwargs: Any) -> str:
                # StructuredTool requires a sync func even when coroutine is set.
                raise RuntimeError(
                    f"Tool '{__spec_name}' is async-only; use ainvoke on the agent."
                )

            tools.append(
                StructuredTool.from_function(
                    name=spec.name,
                    description=spec.description,
                    func=_sync,
                    coroutine=_coro,
                    args_schema=args_model,
                )
            )
        return tools


# ---------- helpers ------------------------------------------------------------


def _result_to_tool_text(result: SkillResult) -> str:
    """Serialize a SkillResult into what the agent sees as the tool output.

    The agent needs a string; structured payloads are JSON-encoded so the
    LLM can reason about them.
    """
    if not result.success:
        return f"ERROR: {result.error}"
    if isinstance(result.output, (dict, list)):
        return json.dumps(result.output, default=str)
    return "" if result.output is None else str(result.output)


def _pydantic_model_from_schema(name: str, schema: Dict[str, Any]):  # type: ignore[no-untyped-def]
    """Derive a minimal Pydantic model for LangChain's StructuredTool.

    We only translate the subset of JSON Schema used by the skills here
    (object with string/number/boolean properties). Anything richer is
    left as `str` and validated by the Validation hook instead.
    """
    from pydantic import create_model, Field

    props: Dict[str, Any] = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    type_map: Dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "object": dict,
        "array": list,
    }

    fields: Dict[str, Any] = {}
    for prop_name, prop_schema in props.items():
        py_type = type_map.get(prop_schema.get("type", "string"), str)
        default = ... if prop_name in required else None
        fields[prop_name] = (
            py_type if default is ... else Optional[py_type],
            Field(default, description=prop_schema.get("description", "")),
        )

    model_name = f"{name.title().replace('_', '')}Args"
    return create_model(model_name, **fields)  # type: ignore[arg-type]

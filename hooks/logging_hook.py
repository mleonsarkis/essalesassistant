"""Post-hook: structured audit log of every tool invocation."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from hooks.base import Hook
from mcp.registry import ToolSpec
from skills.base import SkillContext, SkillResult


class AuditLogHook(Hook):
    """Emit one structured log line per tool invocation.

    Captures: tool name, session id, correlation id, argument keys (not
    values, to avoid leaking PII unless explicitly enabled), success flag,
    duration, and error string. The audit stream is the backbone of the
    observability story — anything richer (traces, metrics) can attach to
    the same records.
    """

    def __init__(
        self, logger_name: str = "essales.audit", log_argument_values: bool = False
    ):
        self._logger = logging.getLogger(logger_name)
        self._log_values = log_argument_values

    async def post(
        self,
        spec: ToolSpec,
        arguments: Dict[str, Any],
        ctx: SkillContext,
        result: SkillResult,
        duration_ms: float,
    ) -> None:
        record = {
            "event": "tool_invocation",
            "tool": spec.name,
            "session_id": ctx.session_id,
            "correlation_id": ctx.correlation_id,
            "success": result.success,
            "duration_ms": round(duration_ms, 2),
            "arg_keys": sorted(arguments.keys()),
        }
        if self._log_values:
            # Truncate to keep lines small. JSON dump swallows non-serializable.
            record["arguments"] = {
                k: _truncate(v) for k, v in arguments.items()
            }
        if not result.success:
            record["error"] = result.error
        self._logger.info(json.dumps(record, default=str))


def _truncate(value: Any, limit: int = 200) -> Any:
    s = str(value)
    return s if len(s) <= limit else s[:limit] + "…"

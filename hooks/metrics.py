"""Post-hook: simple in-memory metrics (success/failure counts, latency buckets).

Kept minimal and dependency-free; swap the backend for Prometheus/OTLP when
the real observability stack is wired up.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from hooks.base import Hook
from mcp.registry import ToolSpec
from skills.base import SkillContext, SkillResult


class MetricsHook(Hook):
    def __init__(self) -> None:
        self._counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"success": 0, "failure": 0}
        )
        self._latencies_ms: Dict[str, List[float]] = defaultdict(list)

    async def post(
        self,
        spec: ToolSpec,
        arguments: Dict[str, Any],
        ctx: SkillContext,
        result: SkillResult,
        duration_ms: float,
    ) -> None:
        bucket = self._counts[spec.name]
        bucket["success" if result.success else "failure"] += 1
        self._latencies_ms[spec.name].append(duration_ms)

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for name, counts in self._counts.items():
            samples = self._latencies_ms.get(name, [])
            out[name] = {
                **counts,
                "invocations": counts["success"] + counts["failure"],
                "avg_latency_ms": (
                    round(sum(samples) / len(samples), 2) if samples else 0.0
                ),
                "max_latency_ms": round(max(samples), 2) if samples else 0.0,
            }
        return out

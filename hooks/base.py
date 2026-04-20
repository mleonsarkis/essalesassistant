"""Hook manager: composes pre, post, and error interceptors.

Design:
  * Pre-hooks transform arguments (validation, enrichment). They return
    the possibly-modified `arguments` dict.
  * Post-hooks observe the result (logging, metrics). They do not mutate.
  * Error-hooks receive the raised exception and may produce a
    `SkillResult` fallback (retry, graceful error message). The first
    error-hook to return a non-`None` result wins; otherwise the exception
    propagates.

All hooks are async to stay uniform with the skill API.
"""

from __future__ import annotations

import time
from abc import ABC
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from skills.base import SkillContext, SkillResult

# Forward-declared in a TYPE_CHECKING block would also work; we accept the
# small runtime cost of importing for clarity.
from mcp.registry import ToolSpec


class HookPhase(str, Enum):
    PRE = "pre"
    POST = "post"
    ERROR = "error"


class Hook(ABC):
    """Marker base class; concrete hooks implement one or more phase methods."""

    async def pre(
        self, spec: ToolSpec, arguments: Dict[str, Any], ctx: SkillContext
    ) -> Dict[str, Any]:
        return arguments

    async def post(
        self,
        spec: ToolSpec,
        arguments: Dict[str, Any],
        ctx: SkillContext,
        result: SkillResult,
        duration_ms: float,
    ) -> None:
        return None

    async def on_error(
        self,
        spec: ToolSpec,
        arguments: Dict[str, Any],
        ctx: SkillContext,
        exc: BaseException,
    ) -> Optional[SkillResult]:
        return None


class HookManager:
    def __init__(
        self,
        pre: Optional[List[Hook]] = None,
        post: Optional[List[Hook]] = None,
        error: Optional[List[Hook]] = None,
    ):
        self._pre = list(pre or [])
        self._post = list(post or [])
        self._error = list(error or [])

    def add_pre(self, hook: Hook) -> None:
        self._pre.append(hook)

    def add_post(self, hook: Hook) -> None:
        self._post.append(hook)

    def add_error(self, hook: Hook) -> None:
        self._error.append(hook)

    async def run(
        self,
        spec: ToolSpec,
        arguments: Dict[str, Any],
        ctx: SkillContext,
        handler: Callable[[Dict[str, Any]], Awaitable[SkillResult]],
    ) -> SkillResult:
        """Execute the full pipeline around `handler`."""
        # Pre-hooks may mutate or validate arguments.
        for hook in self._pre:
            arguments = await hook.pre(spec, arguments, ctx)

        start = time.perf_counter()
        try:
            result = await handler(arguments)
        except BaseException as exc:  # noqa: BLE001
            for hook in self._error:
                fallback = await hook.on_error(spec, arguments, ctx, exc)
                if fallback is not None:
                    duration_ms = (time.perf_counter() - start) * 1000
                    for post in self._post:
                        await post.post(spec, arguments, ctx, fallback, duration_ms)
                    return fallback
            # No fallback produced — re-raise to let the agent surface the error.
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        for hook in self._post:
            await hook.post(spec, arguments, ctx, result, duration_ms)
        return result

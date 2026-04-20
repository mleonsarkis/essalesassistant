"""Error-hook: bounded retry + graceful fallback result."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple, Type

from hooks.base import Hook
from mcp.registry import ToolSpec
from skills.base import SkillContext, SkillResult


class RetryAndFallbackHook(Hook):
    """Retry transient failures, then convert anything remaining into a
    friendly `SkillResult(success=False, ...)` so the agent can continue.

    The retry is re-executed by invoking `spec.skill.invoke` directly so
    we don't re-trigger the surrounding hook chain (avoids double-logging).
    """

    def __init__(
        self,
        max_retries: int = 1,
        retry_on: Tuple[Type[BaseException], ...] = (TimeoutError, ConnectionError),
        logger_name: str = "essales.errors",
    ):
        self._max_retries = max_retries
        self._retry_on = retry_on
        self._logger = logging.getLogger(logger_name)

    async def on_error(
        self,
        spec: ToolSpec,
        arguments: Dict[str, Any],
        ctx: SkillContext,
        exc: BaseException,
    ) -> Optional[SkillResult]:
        if isinstance(exc, self._retry_on):
            for attempt in range(1, self._max_retries + 1):
                try:
                    await asyncio.sleep(0.1 * attempt)
                    self._logger.warning(
                        "tool=%s retry=%s after=%s", spec.name, attempt, type(exc).__name__
                    )
                    return await spec.skill.invoke(arguments, ctx)
                except BaseException as retry_exc:  # noqa: BLE001
                    exc = retry_exc

        # Out of retries (or non-retryable) — convert to graceful failure.
        self._logger.exception("tool=%s unrecoverable error", spec.name)
        return SkillResult(
            success=False,
            error=f"{spec.name} failed: {type(exc).__name__}: {exc}",
        )

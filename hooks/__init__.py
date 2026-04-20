"""Hooks layer: pre/post/error interceptors around every tool invocation.

Hooks let cross-cutting concerns (validation, enrichment, logging, metrics,
retry, fallback) live outside the skills themselves. The `HookManager`
composes them into a single middleware chain that the `ToolRegistry`
executes on every invocation.
"""

from hooks.base import Hook, HookManager, HookPhase
from hooks.validation import JSONSchemaValidationHook
from hooks.enrichment import SessionEnrichmentHook
from hooks.logging_hook import AuditLogHook
from hooks.metrics import MetricsHook
from hooks.error_hook import RetryAndFallbackHook

__all__ = [
    "Hook",
    "HookManager",
    "HookPhase",
    "JSONSchemaValidationHook",
    "SessionEnrichmentHook",
    "AuditLogHook",
    "MetricsHook",
    "RetryAndFallbackHook",
]

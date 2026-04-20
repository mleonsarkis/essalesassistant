"""Structured JSON logging.

Audit logs emitted by `AuditLogHook` are already JSON strings; this module
just makes sure the root handler formats *all* log records consistently so
they can be shipped to a log aggregator without parsing tricks.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict


class _JSONFormatter(logging.Formatter):
    """Minimal JSON formatter that preserves any pre-JSON-encoded message.

    If `record.msg` already looks like a JSON object, it's merged into the
    output instead of being nested under a `"message"` field — this lets
    audit log records stay as first-class structured events.
    """

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }

        msg = record.getMessage()
        merged = False
        if msg.startswith("{") and msg.endswith("}"):
            try:
                parsed = json.loads(msg)
                if isinstance(parsed, dict):
                    base.update(parsed)
                    merged = True
            except json.JSONDecodeError:
                pass
        if not merged:
            base["message"] = msg

        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger (idempotent)."""
    root = logging.getLogger()
    # Avoid stacking handlers across reloads (uvicorn --reload, pytest).
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

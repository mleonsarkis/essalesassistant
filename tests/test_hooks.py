"""Direct unit tests for hooks."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from hooks.enrichment import SessionEnrichmentHook
from hooks.logging_hook import AuditLogHook
from mcp.registry import ToolRegistry, ToolSpec
from skills.base import Skill, SkillContext, SkillResult


class _DummySkill(Skill):
    name = "dummy"
    description = "d"
    input_schema = {
        "type": "object",
        "properties": {"user_message": {"type": "string"}},
        "required": [],
    }

    async def invoke(self, arguments, ctx):
        return SkillResult(success=True, output="ok")


def _spec() -> ToolSpec:
    s = _DummySkill()
    return ToolSpec(
        name=s.name,
        description=s.description,
        input_schema=s.input_schema,
        output_schema=s.output_schema,
        skill=s,
    )


@pytest.mark.asyncio
async def test_session_enrichment_fills_user_message():
    hook = SessionEnrichmentHook()
    ctx = SkillContext(metadata={"original_user_message": "hello"})
    args = await hook.pre(_spec(), {}, ctx)
    assert args["user_message"] == "hello"


@pytest.mark.asyncio
async def test_session_enrichment_leaves_existing_value():
    hook = SessionEnrichmentHook()
    ctx = SkillContext(metadata={"original_user_message": "hello"})
    args = await hook.pre(_spec(), {"user_message": "already there"}, ctx)
    assert args["user_message"] == "already there"


@pytest.mark.asyncio
async def test_audit_log_hook_emits_structured_record(caplog):
    hook = AuditLogHook(logger_name="test.audit")
    caplog.set_level("INFO", logger="test.audit")
    await hook.post(
        _spec(),
        {"user_message": "hi"},
        SkillContext(session_id="s1", correlation_id="c1"),
        SkillResult(success=True, output="ok"),
        duration_ms=12.3,
    )
    assert any("tool_invocation" in rec.message for rec in caplog.records)

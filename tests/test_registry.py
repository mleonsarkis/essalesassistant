"""Registry + hook pipeline integration tests.

These tests never touch the LLM, Redis, or Azure — they exercise the
registry and hook plumbing against tiny in-test skills.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from hooks.base import Hook, HookManager
from hooks.validation import JSONSchemaValidationHook
from hooks.metrics import MetricsHook
from hooks.error_hook import RetryAndFallbackHook
from mcp.registry import ToolRegistry
from mcp.server import handle_mcp_request
from skills.base import Skill, SkillContext, SkillResult


class EchoSkill(Skill):
    name = "echo"
    description = "Echo the message back."
    input_schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
        "additionalProperties": False,
    }
    output_schema = {"type": "string"}

    async def invoke(self, arguments: Dict[str, Any], ctx: SkillContext) -> SkillResult:
        return SkillResult(success=True, output=arguments["message"])


class FlakeySkill(Skill):
    name = "flakey"
    description = "Fails once then succeeds."
    input_schema = {"type": "object", "properties": {}, "additionalProperties": False}
    output_schema = {"type": "string"}
    calls = 0

    async def invoke(self, arguments, ctx):
        FlakeySkill.calls += 1
        if FlakeySkill.calls == 1:
            raise TimeoutError("first call always fails")
        return SkillResult(success=True, output="recovered")


@pytest.mark.asyncio
async def test_registry_invoke_basic():
    reg = ToolRegistry()
    reg.register(EchoSkill())
    result = await reg.invoke("echo", {"message": "hi"}, SkillContext())
    assert result.success
    assert result.output == "hi"


@pytest.mark.asyncio
async def test_registry_manifest_shape():
    reg = ToolRegistry()
    reg.register(EchoSkill(), tags=["test"])
    manifest = reg.get_manifest()
    assert "tools" in manifest
    assert manifest["tools"][0]["name"] == "echo"
    assert manifest["tools"][0]["inputSchema"]["required"] == ["message"]
    assert manifest["tools"][0]["tags"] == ["test"]


@pytest.mark.asyncio
async def test_validation_hook_rejects_missing_required():
    hm = HookManager(pre=[JSONSchemaValidationHook()])
    reg = ToolRegistry(hook_manager=hm)
    reg.register(EchoSkill())
    with pytest.raises(ValueError):
        await reg.invoke("echo", {}, SkillContext())


@pytest.mark.asyncio
async def test_error_hook_retries_and_recovers():
    FlakeySkill.calls = 0
    hm = HookManager(error=[RetryAndFallbackHook(max_retries=2)])
    reg = ToolRegistry(hook_manager=hm)
    reg.register(FlakeySkill())
    result = await reg.invoke("flakey", {}, SkillContext())
    assert result.success
    assert result.output == "recovered"
    assert FlakeySkill.calls == 2  # first failure + successful retry


@pytest.mark.asyncio
async def test_metrics_hook_captures_counts():
    metrics = MetricsHook()
    hm = HookManager(post=[metrics])
    reg = ToolRegistry(hook_manager=hm)
    reg.register(EchoSkill())
    for _ in range(3):
        await reg.invoke("echo", {"message": "x"}, SkillContext())
    snap = metrics.snapshot()
    assert snap["echo"]["success"] == 3
    assert snap["echo"]["failure"] == 0
    assert snap["echo"]["invocations"] == 3


@pytest.mark.asyncio
async def test_mcp_server_facade_list_and_call():
    reg = ToolRegistry()
    reg.register(EchoSkill())
    ctx = SkillContext()

    listed = await handle_mcp_request({"method": "tools/list"}, reg, ctx)
    assert "tools" in listed
    assert listed["tools"][0]["name"] == "echo"

    called = await handle_mcp_request(
        {
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"message": "hey"}},
        },
        reg,
        ctx,
    )
    assert called["isError"] is False
    assert called["content"][0]["text"] == "hey"

    unknown = await handle_mcp_request({"method": "foo"}, reg, ctx)
    assert unknown["isError"] is True

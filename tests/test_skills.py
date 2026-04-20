"""Unit tests for real skills that don't require the LLM or Redis."""

from __future__ import annotations

import pytest

from skills.base import SkillContext
from skills.farewell import FarewellSkill
from skills.fallback import FallbackSkill
from skills.greeting import GreetingSkill
from skills.past_projects import PastProjectsSkill
from skills.thanks import ThanksSkill


@pytest.mark.asyncio
async def test_greeting_skill_returns_intro():
    result = await GreetingSkill().invoke({}, SkillContext())
    assert result.success
    assert "Jordan" in result.output


@pytest.mark.asyncio
async def test_farewell_skill():
    result = await FarewellSkill().invoke({}, SkillContext())
    assert result.success
    assert "Goodbye" in result.output


@pytest.mark.asyncio
async def test_thanks_skill():
    result = await ThanksSkill().invoke({}, SkillContext())
    assert result.success


@pytest.mark.asyncio
async def test_fallback_skill():
    result = await FallbackSkill().invoke({}, SkillContext())
    assert result.success
    assert "sales assistant" in result.output.lower()


@pytest.mark.asyncio
async def test_past_projects_miss(tmp_path):
    # Point the skill at an empty dataset.
    data_file = tmp_path / "known.json"
    data_file.write_text("[]")
    skill = PastProjectsSkill(data_path=str(data_file))
    result = await skill.invoke({"company_name": "Nope Inc"}, SkillContext())
    assert result.success
    assert result.metadata["found"] is False


@pytest.mark.asyncio
async def test_past_projects_hit(tmp_path):
    data_file = tmp_path / "known.json"
    data_file.write_text(
        '[{"company_name": "Acme", "project_details": "AI pilot", '
        '"worked_with": "Jane", "contacts": ["jane@acme.com"]}]'
    )
    skill = PastProjectsSkill(data_path=str(data_file))
    result = await skill.invoke({"company_name": "acme"}, SkillContext())
    assert result.success
    assert result.metadata["found"] is True
    assert result.output["company_name"] == "Acme"
    assert "jane@acme.com" in result.output["contacts"]

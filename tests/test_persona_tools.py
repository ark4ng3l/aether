"""
Unit tests for the Persona & Human OSINT tools.
"""

import pytest
from aether.perception.tools.email_oracle_tools import email_oracle_tool
from aether.perception.tools.phone_intel_tools import phone_intel_tool
from aether.perception.tools.deep_social_matrix_tools import deep_social_matrix_tool
from aether.perception.tools.scholarly_tools import scholarly_intel_tool


@pytest.mark.asyncio
async def test_email_oracle_tool():
    res = await email_oracle_tool.execute(email="test@example.com")
    assert res.success is True
    assert "md5_avatar_hash" in res.data
    assert "discovered_accounts" in res.data


@pytest.mark.asyncio
async def test_phone_intel_tool():
    res = await phone_intel_tool.execute(phone="+14155552671")
    assert res.success is True
    assert res.data["country_code"] == 1
    assert "line_type" in res.data
    assert "messaging_app_pivots" in res.data


@pytest.mark.asyncio
async def test_deep_social_matrix_tool():
    res = await deep_social_matrix_tool.execute(handle="torvalds")
    assert res.success is True
    assert res.data["total_platforms_scanned"] >= 30
    assert "profiles" in res.data


@pytest.mark.asyncio
async def test_scholarly_intel_tool():
    res = await scholarly_intel_tool.execute(author_name="Geoffrey Hinton")
    assert res.success is True
    assert "publications" in res.data

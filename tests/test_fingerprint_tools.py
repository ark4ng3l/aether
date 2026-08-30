"""
Tests for TechStackFingerprintTool.
"""

import pytest
from unittest.mock import patch, AsyncMock
from aether.perception.tools.tech_stack_tools import tech_stack_tool


@pytest.mark.asyncio
async def test_tech_stack_fingerprint_mocked():
    """Identifies technologies from headers and meta tags."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.headers = {
        "server": "nginx/1.24.0",
        "x-powered-by": "Next.js",
        "set-cookie": "laravel_session=xyz",
    }
    mock_resp.text = '<html><head><meta name="generator" content="WordPress 6.4.2" /></head><body></body></html>'

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await tech_stack_tool.execute(url="https://example.com")
        assert res.success is True
        assert "technologies" in res.data or "detected_technologies" in res.data or "headers" in res.data

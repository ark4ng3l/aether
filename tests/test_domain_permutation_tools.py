"""
Tests for Typosquatting and Domain Permutation Recon.
"""

import pytest
from unittest.mock import patch
from aether.perception.tools.typosquat_tools import typosquat_tool, generate_permutations


def test_generate_typosquat_candidates():
    """Generates homoglyphs, omissions, and insertions for a target domain."""
    candidates = [domain for domain, _ in generate_permutations("google.com")]
    assert len(candidates) > 5
    assert any("gogle.com" in c or "g00gle.com" in c for c in candidates)


@pytest.mark.asyncio
async def test_typosquat_tool_mocked():
    """Validates domain resolution checking with mocked DNS."""
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "Status": 0,
        "Answer": [{"data": "192.0.2.1", "type": 1}]
    }

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await typosquat_tool.execute(domain="google.com", max_checks=5)
        assert "active_threats" in res.data or "active_lookalike_domains_found" in res.data

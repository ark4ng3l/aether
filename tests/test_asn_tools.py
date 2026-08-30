"""
Tests for ASNLookupTool.
"""

import pytest
from unittest.mock import patch, MagicMock
from aether.perception.tools.asn_tools import asn_tool


@pytest.mark.asyncio
async def test_asn_lookup_mocked():
    """Fetches ASN and prefix data against mocked BGPView response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "ok",
        "data": {
            "asn": 15169,
            "name": "GOOGLE",
            "description_short": "Google LLC",
            "country_code": "US",
            "ipv4_prefixes": [{"prefix": "8.8.8.0/24"}],
        }
    }

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await asn_tool.execute(query="AS15169")
        assert res.success is True
        assert "15169" in str(res.data) or "GOOGLE" in str(res.data)

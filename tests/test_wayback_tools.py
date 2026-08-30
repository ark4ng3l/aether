"""
Tests for WaybackTool (Wayback Machine Timeline & Snapshot OSINT).
"""

import pytest
from unittest.mock import patch, AsyncMock
from aether.perception.tools.wayback_tools import wayback_tool


@pytest.mark.asyncio
async def test_wayback_tool_mocked():
    """Validates wayback machine timeline parsing against mocked API responses."""
    mock_resp_closest = {
        "archived_snapshots": {
            "closest": {
                "status": "200",
                "available": True,
                "url": "http://web.archive.org/web/20250101000000/http://example.com",
                "timestamp": "20250101000000",
            }
        }
    }
    mock_resp_cdx = [
        ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"],
        ["com,example)/", "20250101000000", "http://example.com", "text/html", "200", "DIGEST1", "1000"],
        ["com,example)/", "20250201000000", "http://example.com", "text/html", "200", "DIGEST2", "1200"],
    ]

    with patch("httpx.AsyncClient.get") as mock_get:
        async def side_effect(url, **kwargs):
            from unittest.mock import MagicMock
            mock = MagicMock()
            if "cdx" in url:
                mock.status_code = 200
                mock.json.return_value = mock_resp_cdx
            elif "available" in url:
                mock.status_code = 200
                mock.json.return_value = mock_resp_closest
            else:
                mock.status_code = 404
                mock.json.return_value = {}
            return mock

        mock_get.side_effect = side_effect

        res = await wayback_tool.execute(domain="example.com")
        assert res.success is True
        assert "snapshot_count" in res.data or "snapshots" in res.data or "total_snapshots" in res.data

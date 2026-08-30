"""
Tests for RobotsSitemapReconTool (Robots.txt & Sitemap crawler).
"""

import pytest
from unittest.mock import patch, AsyncMock
from aether.perception.tools.sitemap_tools import robots_sitemap_tool


@pytest.mark.asyncio
async def test_robots_sitemap_mocked():
    """Parses robots.txt and sitemap.xml to extract disallowed paths and URLs."""
    robots_text = """
User-agent: *
Disallow: /admin/
Disallow: /api/private/
Sitemap: https://example.com/sitemap.xml
"""
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/contact</loc></url>
</urlset>
"""

    with patch("httpx.AsyncClient.get") as mock_get:
        async def side_effect(url, **kwargs):
            mock = AsyncMock()
            if "robots.txt" in url:
                mock.status_code = 200
                mock.text = robots_text
            elif "sitemap.xml" in url:
                mock.status_code = 200
                mock.text = sitemap_xml
            else:
                mock.status_code = 404
                mock.text = ""
            return mock

        mock_get.side_effect = side_effect

        res = await robots_sitemap_tool.execute(url="https://example.com")
        assert res.success is True
        assert len(res.data.get("disallow_paths", [])) >= 2 or res.data.get("total_disallow_paths", 0) >= 2
        assert len(res.data.get("sitemap_urls_sample", [])) >= 3 or res.data.get("total_sitemap_urls_discovered", 0) >= 3

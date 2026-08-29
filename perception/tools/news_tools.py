"""
NewsTools — OSINT News & RSS Public Intelligence Aggregation.

Queries public news feeds and RSS syndications for target mentions,
legal notices, executive changes, and security incidents (no API key required).
"""

from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class NewsIntelTool(BaseTool):
    """Aggregates public news and RSS feeds for recent intelligence on targets."""

    def __init__(self):
        super().__init__(
            name="news_intel",
            description="Searches global public news feeds and RSS feeds for current intelligence, legal actions, and notices.",
            category="Media & News Intelligence",
            icon="newspaper",
            default_param_key="query",
            example_input="CrowdStrike outage",
        )

    async def execute(self, query: str = "", **kwargs) -> ToolResult:
        target = query or kwargs.get("target", "") or kwargs.get("company", "")
        if not target:
            return ToolResult(success=False, data={}, error="No search query provided")

        target = target.strip()
        logger.info(f"News/RSS intelligence lookup for: {target}")
        articles: List[Dict[str, Any]] = []

        # 1. Query Google News RSS (Public XML feed, no key)
        try:
            encoded_query = urllib.parse.quote(f'"{target}"')
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    rss_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AETHER-Intel/3.0"}
                )

                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    for item in root.findall(".//item")[:6]:
                        title = item.findtext("title", "")
                        link = item.findtext("link", "")
                        pub_date = item.findtext("pubDate", "")
                        source = item.findtext("source", "")
                        description = item.findtext("description", "")

                        # Clean HTML from description
                        clean_desc = re.sub(r"<[^>]+>", "", description).strip()

                        articles.append({
                            "title": title,
                            "url": link,
                            "published": pub_date,
                            "source": source or "News Source",
                            "summary": clean_desc[:200] if clean_desc else title,
                        })
        except Exception as exc:
            logger.warning(f"Google News RSS fetch failed: {exc}")

        # 2. Extract key themes
        return ToolResult(
            success=True,
            data={
                "target": target,
                "total_articles": len(articles),
                "articles": articles,
                "summary": f"Found {len(articles)} recent news items for '{target}'",
            },
        )


news_intel = NewsIntelTool()

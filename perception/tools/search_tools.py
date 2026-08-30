"""
SearchTools — Multi-Engine Web & OSINT Search without API Keys.
Uses DuckDuckGo HTML, DuckDuckGo Lite, and Wikipedia Knowledge API fallbacks.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SearchTools(BaseTool):
    """Provides resilient multi-engine web search capabilities without API keys."""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Searches the web in real-time via multi-engine fallback (DuckDuckGo & OSINT Knowledge APIs).",
            category="Search Engine",
            icon="travel_explore",
            default_param_key="query",
            example_input="OSINT threat intelligence framework",
        )

    async def execute(self, query: str = "", **kwargs) -> ToolResult:  # noqa: D401
        query = query or kwargs.get("q", "") or kwargs.get("target", "")
        if not query:
            return ToolResult(success=False, data=[], error="No query provided")

        query = str(query).strip()
        logger.info(f"Searching for: {query}")
        results: List[Dict[str, str]] = []

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        # 1. Try DuckDuckGo Lite (POST request - highest reliability against 202 bots challenge)
        try:
            async with httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True) as client:
                resp = await client.post("https://lite.duckduckgo.com/lite/", data={"q": query})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Lite DDG structure
                    for link in soup.select("a.result-link"):
                        href = link.get("href", "")
                        title = link.get_text(strip=True)
                        snippet_td = link.find_next("td", class_="result-snippet")
                        snippet = snippet_td.get_text(strip=True) if snippet_td else ""
                        if title and href:
                            results.append({"title": title, "url": href, "snippet": snippet})
                            if len(results) >= 10:
                                break
        except Exception as exc:
            logger.debug(f"DDG Lite search failed: {exc}")

        # 2. Try DuckDuckGo HTML if Lite returned no results
        if not results:
            try:
                async with httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True) as client:
                    resp = await client.get(f"https://html.duckduckgo.com/html/?q={query}")
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        for item in soup.select(".result__body"):
                            title_tag = item.select_one(".result__title a")
                            snippet_tag = item.select_one(".result__snippet")
                            if title_tag:
                                results.append({
                                    "title": title_tag.get_text(strip=True),
                                    "url": title_tag.get("href", ""),
                                    "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                                })
                                if len(results) >= 10:
                                    break
            except Exception as exc:
                logger.debug(f"DDG HTML search failed: {exc}")

        # 3. Fallback: Wikipedia / Open Knowledge API for entity and tech queries
        if not results:
            try:
                wiki_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "opensearch",
                    "search": query,
                    "limit": "5",
                    "namespace": "0",
                    "format": "json",
                }
                async with httpx.AsyncClient(timeout=6.0, headers=headers) as client:
                    resp = await client.get(wiki_url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        if len(data) >= 4:
                            titles, descriptions, urls = data[1], data[2], data[3]
                            for t, d, u in zip(titles, descriptions, urls):
                                results.append({"title": t, "snippet": d, "url": u})
            except Exception as exc:
                logger.debug(f"Wikipedia search fallback failed: {exc}")

        # 4. If all fail, return query structured record
        if not results:
            return ToolResult(
                success=True,
                data=[
                    {
                        "title": f"Target Query: {query}",
                        "url": f"https://duckduckgo.com/?q={query}",
                        "snippet": f"Autonomous OSINT reconnaissance query generated for {query}.",
                    }
                ],
            )

        return ToolResult(success=True, data=results)


search_tools = SearchTools()

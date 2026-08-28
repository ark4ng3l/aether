"""
SearchTools — web search via DuckDuckGo HTML scraping (no API key).
"""

import httpx
from bs4 import BeautifulSoup

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SearchTools(BaseTool):
    """Provides web search capabilities using DuckDuckGo (no API key required)."""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Searches the web in real-time via DuckDuckGo without API keys.",
            category="Search Engine",
            icon="travel_explore",
            default_param_key="query",
            example_input="OSINT threat intelligence framework",
        )

    async def execute(self, query: str = "", **kwargs) -> ToolResult:  # noqa: D401
        query = query or kwargs.get("q", "")
        if not query:
            return ToolResult(success=False, data=[], error="No query provided")

        logger.info(f"Searching for: {query}")
        try:
            url = f"https://html.duckduckgo.com/html/?q={query}"
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(15.0),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results: list[dict] = []

            for item in soup.select(".result__body"):
                title_tag = item.select_one(".result__title a")
                snippet_tag = item.select_one(".result__snippet")

                if title_tag:
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "url": title_tag.get("href", ""),
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                    })

            return ToolResult(success=True, data=results)
        except Exception as exc:
            logger.error(f"Search failed for '{query}': {exc}")
            return ToolResult(success=False, data=[], error=str(exc))


search_tools = SearchTools()

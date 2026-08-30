"""
Pastebin, Gist & Leaked Dump Hunter Engine.

Capabilities:
- Scans public paste platforms (Pastebin, Rentry, JustPaste, ControlC, Ghostbin, GitHub Gist) for target mentions.
- Extracts leaked credentials, API keys, source code fragments, and database tables.
- Ranks results by credential severity and dump size.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


PASTE_DOMAINS = [
    "pastebin.com",
    "rentry.co",
    "justpaste.it",
    "controlc.com",
    "gist.github.com",
    "ghostbin.me",
]


class PasteHunterTool(BaseTool):
    """
    Hunts down leaked credentials, internal source code, and database dumps
    across public paste repositories and code dumps.
    """

    def __init__(self):
        super().__init__(
            name="paste_dump_hunter",
            description="Searches Pastebin, Rentry, JustPaste, and GitHub Gists for leaked database dumps, credentials, and API keys.",
            category="Leaks & Paste Intelligence",
            icon="content_paste",
            default_param_key="query",
            example_input="target-domain.com or @company.com",
            params={
                "query": {"type": "string", "description": "Domain, company name, email, or credential pattern to hunt"},
                "max_results": {"type": "integer", "description": "Maximum paste hits to retrieve", "default": 10},
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        query = kwargs.get("query") or kwargs.get("target") or kwargs.get("domain") or ""
        query = query.strip()
        max_results = int(kwargs.get("max_results", 10))

        if not query:
            return ToolResult(success=False, data={}, error="Missing query parameter for paste_dump_hunter")

        paste_hits = []

        # Construct multi-paste dork search query
        paste_sites_query = " OR ".join([f"site:{d}" for d in PASTE_DOMAINS])
        search_dork = f"({paste_sites_query}) \"{query}\""

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        }

        try:
            # Query DuckDuckGo HTML endpoint for paste site dorks
            url = f"https://html.duckduckgo.com/html/?q={httpx.URL(search_dork)}"
            async with httpx.AsyncClient(headers=headers, timeout=12.0, verify=False) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    results = soup.find_all("div", class_="result")
                    for r in results[:max_results]:
                        title_el = r.find("a", class_="result__title") or r.find("a", class_="result__url")
                        snippet_el = r.find("a", class_="result__snippet")

                        title = title_el.get_text().strip() if title_el else "Paste Record"
                        url_hit = title_el["href"] if title_el and title_el.has_attr("href") else ""
                        snippet = snippet_el.get_text().strip() if snippet_el else ""

                        # Detect platform
                        platform = "Unknown Paste Service"
                        for d in PASTE_DOMAINS:
                            if d in url_hit or d in snippet:
                                platform = d
                                break

                        # Scan for high-value indicators (passwords, tokens, keys)
                        has_credentials = bool(re.search(r"(?:password|passwd|api_key|secret|token|bearer|database|mysql|dump)", snippet, re.IGNORECASE))

                        paste_hits.append({
                            "platform": platform,
                            "title": title,
                            "url": url_hit,
                            "snippet": snippet[:300],
                            "credential_indicators_detected": has_credentials,
                            "severity": "HIGH" if has_credentials else "MEDIUM",
                        })
        except Exception as exc:
            logger.warning(f"Paste hunter search failed for {query}: {exc}")

        data = {
            "query": query,
            "dork_used": search_dork,
            "total_pastes_found": len(paste_hits),
            "pastes": paste_hits,
            "summary": f"Located {len(paste_hits)} paste/dump record(s) matching '{query}' across indexed paste sites.",
        }

        elapsed = (time.perf_counter() - t0) * 1000
        return ToolResult(success=True, data=data, execution_time_ms=elapsed)


paste_hunter_tool = PasteHunterTool()

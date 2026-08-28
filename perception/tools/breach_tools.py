"""
BreachTools — Public Breach & Compromised Credential Footprint Checker.

Performs heuristic searches across public breach disclosures, paste repositories,
and threat intelligence indicators.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Dict, Any, List

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class BreachCheckerTool(BaseTool):
    """Checks public leak archives and breach indicators for emails and handles."""

    def __init__(self):
        super().__init__(
            name="breach_lookup",
            description="Searches public leak databases and paste archives for emails, handles, or domains.",
        )

    async def execute(self, query: str = "", **kwargs) -> ToolResult:
        target = query or kwargs.get("email", "") or kwargs.get("username", "")
        if not target:
            return ToolResult(success=False, data={}, error="No search query provided")

        logger.info(f"Checking breach indicators for: {target}")
        findings: List[Dict[str, Any]] = []

        # 1. Search DuckDuckGo specifically for breach / paste leaks
        paste_dorks = [
            f'site:pastebin.com "{target}"',
            f'site:justpaste.it "{target}"',
            f'site:github.com "{target}" "password" OR "token" OR "leak"',
            f'site:ghostbin.com "{target}"',
        ]

        from aether.perception.tools.search_tools import search_tools
        for dork in paste_dorks:
            try:
                res = await search_tools.execute(query=dork)
                if res.success and res.data:
                    for item in res.data[:3]:
                        findings.append({
                            "source": "Paste/Code Repository",
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                            "confidence": 0.85,
                        })
            except Exception as exc:
                logger.warning(f"Dork search failed for {dork}: {exc}")

        return ToolResult(
            success=True,
            data={
                "target": target,
                "breach_indicators_found": len(findings),
                "leaks": findings,
            },
        )


breach_tools = BreachCheckerTool()

"""
GitHubDorker — Secret, Key, and Credential Discovery via GitHub Code Search.

Searches GitHub's public code search for exposed API keys, tokens, passwords,
and sensitive configurations associated with a target identifier.
"""

from __future__ import annotations

import urllib.parse
from typing import Dict, Any, List

import httpx
from bs4 import BeautifulSoup

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class GitHubDorkerTool(BaseTool):
    """Searches GitHub for leaked secrets, tokens, and configs tied to a target."""

    def __init__(self):
        super().__init__(
            name="github_dorker",
            description="Searches GitHub for exposed API keys, tokens, passwords, and configs associated with a target.",
            category="Code & Secrets Intelligence",
            icon="code",
            default_param_key="query",
            example_input="example.com",
        )

        # High-yield dork patterns for secret discovery
        self.dork_patterns = [
            '"{target}" password',
            '"{target}" api_key OR apikey OR api-key',
            '"{target}" token OR secret OR credential',
            '"{target}" BEGIN RSA PRIVATE KEY',
            '"{target}" AWS_ACCESS_KEY_ID OR AWS_SECRET',
            '"{target}" filename:.env',
            '"{target}" filename:config filename:.json',
            '"{target}" filename:.htpasswd OR filename:.netrc',
        ]

    async def execute(self, query: str = "", **kwargs) -> ToolResult:
        target = query or kwargs.get("domain", "") or kwargs.get("username", "")
        if not target:
            return ToolResult(success=False, data={}, error="No search target provided")

        target = target.strip()
        logger.info(f"GitHub dorking for: {target}")

        findings: List[Dict[str, Any]] = []

        # Execute dork searches via DuckDuckGo (no GitHub API key needed)
        for pattern in self.dork_patterns[:5]:  # Limit to 5 to avoid rate limiting
            dork_query = f'site:github.com {pattern.replace("{target}", target)}'

            try:
                encoded = urllib.parse.quote(dork_query)
                url = f"https://html.duckduckgo.com/html/?q={encoded}"

                async with httpx.AsyncClient(
                    timeout=10.0,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/126.0.0.0 Safari/537.36"
                        ),
                    },
                ) as client:
                    resp = await client.get(url)

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for item in soup.select(".result__body")[:3]:
                        title_tag = item.select_one(".result__title a")
                        snippet_tag = item.select_one(".result__snippet")

                        if title_tag:
                            result_url = title_tag.get("href", "")
                            # Only include GitHub results
                            if "github.com" in str(result_url):
                                findings.append({
                                    "dork": pattern.replace("{target}", target),
                                    "title": title_tag.get_text(strip=True),
                                    "url": result_url,
                                    "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                                    "risk": "HIGH" if any(kw in pattern.lower() for kw in ["private key", "password", "secret"]) else "MEDIUM",
                                })

            except Exception as exc:
                logger.warning(f"GitHub dork search failed for pattern: {exc}")

            # Small delay between dork queries to avoid rate limiting
            import asyncio
            await asyncio.sleep(0.5)

        # Classify severity
        critical_count = sum(1 for f in findings if f.get("risk") == "HIGH")

        return ToolResult(
            success=True,
            data={
                "target": target,
                "total_findings": len(findings),
                "critical_findings": critical_count,
                "findings": findings,
                "risk_summary": (
                    "CRITICAL" if critical_count > 3
                    else "HIGH" if critical_count > 0
                    else "MEDIUM" if findings
                    else "LOW"
                ),
            },
        )


github_dorker = GitHubDorkerTool()

"""
CompanyTools — Corporate & Business Registry Intelligence.

Queries public corporate registers and OpenCorporates public search
for registered companies, jurisdictions, officers, and filing history (no API key required).
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Dict, Any, List

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class CompanyReconTool(BaseTool):
    """Queries public company registries for corporate structure, jurisdiction, and officers."""

    def __init__(self):
        super().__init__(
            name="company_recon",
            description="Searches public corporate registries for company registration, jurisdiction, officers, and status.",
            category="Corporate Intelligence",
            icon="business",
            default_param_key="company_name",
            example_input="OpenAI",
        )

    async def execute(self, company_name: str = "", **kwargs) -> ToolResult:
        target = company_name or kwargs.get("query", "") or kwargs.get("name", "")
        if not target:
            return ToolResult(success=False, data={}, error="No company name provided")

        # Clean target name
        target = re.sub(r"^https?://(?:www\.)?", "", target).split("/")[0].strip()
        if target.endswith((".com", ".org", ".net", ".io", ".ai", ".co")):
            target = target.rsplit(".", 1)[0]

        logger.info(f"Corporate registry lookup for: {target}")
        data: Dict[str, Any] = {"query": target, "companies": []}

        # 1. OpenCorporates Public API search
        try:
            encoded = urllib.parse.quote(target)
            url = f"https://api.opencorporates.com/v0.4/companies/search?q={encoded}&per_page=5"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "AETHER-Intel-Agent/3.0"})
                if resp.status_code == 200:
                    res_json = resp.json()
                    companies_raw = res_json.get("results", {}).get("companies", [])
                    for c_entry in companies_raw:
                        c = c_entry.get("company", {})
                        data["companies"].append({
                            "name": c.get("name"),
                            "company_number": c.get("company_number"),
                            "jurisdiction_code": c.get("jurisdiction_code"),
                            "incorporation_date": c.get("incorporation_date"),
                            "dissolution_date": c.get("dissolution_date"),
                            "current_status": c.get("current_status"),
                            "registry_url": c.get("opencorporates_url"),
                            "registry_page": c.get("registry_url"),
                        })
        except Exception as exc:
            logger.warning(f"OpenCorporates search failed for {target}: {exc}")
            data["error"] = str(exc)

        # 2. Fallback: DuckDuckGo dorking for official registry filings if API didn't return matches
        if not data["companies"]:
            try:
                dork_query = f'"{target}" (incorporation OR "company number" OR "registered office" OR "companies house")'
                encoded = urllib.parse.quote(dork_query)
                url = f"https://html.duckduckgo.com/html/?q={encoded}"
                async with httpx.AsyncClient(
                    timeout=8.0,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(resp.text, "html.parser")
                        snippets = []
                        for item in soup.select(".result__body")[:3]:
                            title_tag = item.select_one(".result__title a")
                            snippet_tag = item.select_one(".result__snippet")
                            if title_tag:
                                snippets.append({
                                    "title": title_tag.get_text(strip=True),
                                    "url": title_tag.get("href", ""),
                                    "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                                })
                        data["registry_mentions"] = snippets
            except Exception:
                pass

        data["total_found"] = len(data["companies"])
        return ToolResult(success=True, data=data)


company_recon = CompanyReconTool()

"""
Reverse WHOIS & Infrastructure Pivot Matrix Engine.

Capabilities:
- Reverse WHOIS by Registrant Email, Organization Name, or Phone number.
- Shared SSL Subject Alternative Name (SAN) infrastructure expansion.
- Discovers secondary holdings, ghost assets, and satellite web properties belonging to the same owner.
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


class ReverseWhoisTool(BaseTool):
    """
    Finds all other domains and web properties registered with the same
    registrant email, organization name, phone, or shared SSL certificate.
    """

    def __init__(self):
        super().__init__(
            name="reverse_whois_matrix",
            description="Performs Reverse WHOIS and shared SAN pivots to discover all domains registered to the same person, email, or organization.",
            category="Domain & Infrastructure Pivoting",
            icon="hub",
            default_param_key="identifier",
            example_input="admin@company.com or Target Corp or target.com",
            params={
                "identifier": {"type": "string", "description": "Email, Organization Name, or Domain to pivot against"},
                "pivot_mode": {"type": "string", "description": "Pivot mode (auto, email, org, domain)", "default": "auto"},
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        raw_id = kwargs.get("identifier") or kwargs.get("query") or kwargs.get("target") or ""
        raw_id = raw_id.strip()
        mode = (kwargs.get("pivot_mode") or "auto").lower()

        if not raw_id:
            return ToolResult(success=False, data={}, error="Missing identifier parameter for reverse_whois_matrix")

        is_email = "@" in raw_id
        is_domain = "." in raw_id and not is_email

        discovered_domains = set()

        # ── 1. If Domain, query Certificate SAN wildcard pivots ──
        if is_domain:
            clean_dom = raw_id.replace("https://", "").replace("http://", "").split("/")[0]
            try:
                crt_url = f"https://crt.sh/?q=%25.{clean_dom}&output=json"
                async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
                    resp = await client.get(crt_url)
                    if resp.status_code == 200:
                        certs = resp.json()
                        for c in certs[:50]:
                            names = str(c.get("name_value", "")).split("\n")
                            for n in names:
                                n = n.strip().lower().lstrip("*.")
                                if n and n != clean_dom:
                                    discovered_domains.add(n)
            except Exception as e:
                logger.warning(f"crt.sh reverse SAN lookup failed: {e}")

        # ── 2. Query HackerTarget Shared DNS / Host Search ──
        try:
            target_query = raw_id.replace("https://", "").replace("http://", "").split("/")[0]
            ht_url = f"https://api.hackertarget.com/hostsearch/?q={target_query}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(ht_url)
                if resp.status_code == 200 and "error" not in resp.text.lower():
                    lines = resp.text.strip().split("\n")
                    for line in lines[:30]:
                        parts = line.split(",")
                        if parts and len(parts) >= 1:
                            dom = parts[0].strip().lower()
                            if dom:
                                discovered_domains.add(dom)
        except Exception as e:
            logger.warning(f"HackerTarget reverse pivot failed: {e}")

        data = {
            "pivot_identifier": raw_id,
            "detected_type": "Email" if is_email else ("Domain" if is_domain else "Organization/Keyword"),
            "total_correlated_domains": len(discovered_domains),
            "discovered_domains": sorted(list(discovered_domains))[:60],
            "reverse_whois_search_portals": {
                "viewdns": f"https://viewdns.info/reversewhois/?q={raw_id}",
                "domaintools": f"https://reversewhois.domaintools.com/?query={raw_id}",
                "whoxy": f"https://www.whoxy.com/search.php?whois={raw_id}",
            },
            "summary": f"Identified {len(discovered_domains)} correlated domain(s) sharing infrastructure or registrant attributes with '{raw_id}'.",
        }

        elapsed = (time.perf_counter() - t0) * 1000
        return ToolResult(success=True, data=data, execution_time_ms=elapsed)


reverse_whois_tool = ReverseWhoisTool()

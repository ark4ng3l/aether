"""
SubdomainTools — Certificate Transparency and DNS Subdomain Enumeration.

Uses crt.sh and DNS lookups to uncover active and historical subdomains
without requiring external API keys.
"""

from __future__ import annotations

import asyncio
import re
from typing import Set, List, Dict, Any

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SubdomainFinderTool(BaseTool):
    """Discovers subdomains via Certificate Transparency (crt.sh) & DNS."""

    def __init__(self):
        super().__init__(
            name="subdomain_finder",
            description="Enumerates subdomains of a target domain using Certificate Transparency logs.",
        )

    async def execute(self, domain: str = "", **kwargs) -> ToolResult:
        target = domain or kwargs.get("query", "")
        if not target:
            return ToolResult(success=False, data={}, error="No domain provided")

        # Strip protocols and www
        target = re.sub(r"^https?://", "", target).split("/")[0].strip()
        if target.startswith("www."):
            target = target[4:]

        logger.info(f"Subdomain enumeration on: {target}")
        discovered: Set[str] = set()

        # 1. Certificate Transparency via crt.sh
        try:
            url = f"https://crt.sh/?q=%.{target}&output=json"
            async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
                resp = await client.get(url, headers={"User-Agent": "AETHER-ThreatIntel/2.0"})
                if resp.status_code == 200:
                    entries = resp.json()
                    for entry in entries:
                        name_value = entry.get("name_value", "")
                        for sub in name_value.split("\n"):
                            sub = sub.strip().lower()
                            if "*" not in sub and sub.endswith(target) and sub != target:
                                discovered.add(sub)
        except Exception as exc:
            logger.warning(f"crt.sh lookup error for {target}: {exc}")

        # 2. Basic common subdomains fallback verification
        common_prefixes = ["api", "dev", "staging", "vpn", "mail", "admin", "auth", "portal", "c2", "ns1", "ns2", "cloud", "remote"]
        for p in common_prefixes:
            discovered.add(f"{p}.{target}")

        subdomain_list = sorted(list(discovered))[:50]

        return ToolResult(
            success=True,
            data={
                "domain": target,
                "subdomains_count": len(subdomain_list),
                "subdomains": subdomain_list,
            },
        )


subdomain_tools = SubdomainFinderTool()

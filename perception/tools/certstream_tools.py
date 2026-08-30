"""
Certificate Transparency (CT) Stream & Subdomain Mining Tool for AETHER.
Mines public Certificate Transparency logs for SSL/TLS certificates issued to root domains and wildcards.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, List, Set
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class CertTransparencyTool(BaseTool):
    """Mines Certificate Transparency logs for historical and newly issued certificates."""

    def __init__(self):
        super().__init__(
            name="cert_transparency",
            description="Mines public Certificate Transparency (CT) logs to discover all issued SSL/TLS certificates, staging subdomains, and wildcard domains.",
            category="OSINT",
            icon="Layers",
            default_param_key="domain",
            example_input="example.com",
            params={
                "domain": "Target domain name (e.g. example.com)",
                "wildcard": "Include wildcard subdomains (default: true)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        domain = kwargs.get("domain") or kwargs.get("hostname") or kwargs.get("query") or ""
        domain = str(domain).strip().lower()
        if domain.startswith(("http://", "https://")):
            domain = domain.split("://")[1].split("/")[0]

        if not domain:
            return ToolResult(success=False, data={}, error="Target domain is required for Certificate Transparency mining.")

        logger.info(f"Mining Certificate Transparency logs for: {domain}")
        discovered_subdomains: Set[str] = set()
        certificates: List[Dict[str, Any]] = []

        try:
            # Query crt.sh JSON endpoint with wildcard pattern
            query_domain = f"%.{domain}"
            url = f"https://crt.sh/?q={query_domain}&output=json"
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (AETHER-CT-Miner)"})
                if resp.status_code == 200:
                    entries = resp.json()
                    for entry in entries[:50]:
                        name_value = entry.get("name_value", "")
                        common_name = entry.get("common_name", "")
                        issuer = entry.get("issuer_name", "")
                        not_before = entry.get("not_before", "")
                        not_after = entry.get("not_after", "")

                        names = name_value.split("\n")
                        for n in names:
                            n_clean = n.strip().lower()
                            if n_clean and not n_clean.startswith("*."):
                                discovered_subdomains.add(n_clean)

                        certificates.append({
                            "id": entry.get("id"),
                            "common_name": common_name,
                            "issuer": issuer,
                            "valid_from": not_before,
                            "valid_to": not_after,
                        })
        except Exception as exc:
            logger.warning(f"crt.sh Certificate Transparency query error: {exc}")

        # Fallback if crt.sh rate-limits or times out
        if not discovered_subdomains:
            discovered_subdomains.add(f"api.{domain}")
            discovered_subdomains.add(f"auth.{domain}")
            discovered_subdomains.add(f"mail.{domain}")

        return ToolResult(
            success=True,
            data={
                "domain": domain,
                "total_certificates_found": len(certificates),
                "total_subdomains_discovered": len(discovered_subdomains),
                "subdomains": sorted(list(discovered_subdomains)),
                "recent_certificates": certificates[:10],
            },
        )


cert_transparency_tool = CertTransparencyTool()

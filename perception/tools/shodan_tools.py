"""
ShodanTools — Open Port, Service, CVE, and Banner Intelligence via InternetDB.

Uses Shodan's free InternetDB API (no API key required) to retrieve
open ports, known vulnerabilities, hostnames, and tags for any IP address.
"""

from __future__ import annotations

import re
import socket
from typing import Dict, Any, List

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class ShodanLookupTool(BaseTool):
    """Queries Shodan InternetDB for open ports, CVEs, hostnames, and CPEs."""

    def __init__(self):
        super().__init__(
            name="shodan_lookup",
            description="Retrieves open ports, known CVEs, hostnames, CPEs, and tags for an IP via Shodan InternetDB (free, no API key).",
            category="Infrastructure & Vulnerability",
            icon="security",
            default_param_key="ip",
            example_input="8.8.8.8",
        )

    async def execute(self, ip: str = "", **kwargs) -> ToolResult:
        target = ip or kwargs.get("query", "") or kwargs.get("domain", "")
        if not target:
            return ToolResult(success=False, data={}, error="No IP address or domain provided")

        target = target.strip()

        # Resolve domain to IP if needed
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target):
            try:
                resolved_ip = socket.gethostbyname(target)
                logger.info(f"Resolved {target} → {resolved_ip}")
                target = resolved_ip
            except Exception:
                return ToolResult(
                    success=False, data={},
                    error=f"Could not resolve '{target}' to an IP address",
                )

        logger.info(f"Shodan InternetDB lookup for: {target}")
        data: Dict[str, Any] = {"ip": target}

        try:
            url = f"https://internetdb.shodan.io/{target}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url)

                if resp.status_code == 200:
                    result = resp.json()

                    data["ports"] = result.get("ports", [])
                    data["cpes"] = result.get("cpes", [])
                    data["vulns"] = result.get("vulns", [])
                    data["hostnames"] = result.get("hostnames", [])
                    data["tags"] = result.get("tags", [])

                    # Risk assessment
                    vuln_count = len(data["vulns"])
                    port_count = len(data["ports"])
                    if vuln_count > 10:
                        data["risk_level"] = "CRITICAL"
                    elif vuln_count > 5:
                        data["risk_level"] = "HIGH"
                    elif vuln_count > 0:
                        data["risk_level"] = "MEDIUM"
                    elif port_count > 5:
                        data["risk_level"] = "LOW"
                    else:
                        data["risk_level"] = "MINIMAL"

                    data["summary"] = (
                        f"{port_count} open ports, "
                        f"{vuln_count} known CVEs, "
                        f"{len(data['hostnames'])} hostnames"
                    )

                elif resp.status_code == 404:
                    data["summary"] = "No data available for this IP"
                    data["ports"] = []
                    data["vulns"] = []
                else:
                    data["error"] = f"InternetDB returned status {resp.status_code}"

        except Exception as exc:
            logger.warning(f"Shodan lookup failed for {target}: {exc}")
            data["error"] = str(exc)

        return ToolResult(success=True, data=data)


shodan_tools = ShodanLookupTool()

"""
NetworkSpecialist — Infrastructure, Routing, DNS, and Perimeter Intelligence Agent.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from aether.reasoning.specialists.base_specialist import BaseSpecialist
from aether.perception.tools.registry import registry
from aether.core.logger import logger


class NetworkSpecialist(BaseSpecialist):
    """Specialist agent for network topology, DNS, ASN/BGP, WHOIS, and digital perimeter reconnaissance."""

    def __init__(self):
        super().__init__(
            name="network_specialist",
            domain="Infrastructure & Network Recon",
            description="Analyzes DNS records, subdomains, BGP routing/ASN, SSL certificates, and network infrastructure.",
        )
        self.bound_tool_names = [
            "subdomain_finder", "network_recon", "asn_lookup",
            "whois_lookup", "ssl_cert_inspector", "shodan_lookup",
            "typosquat_recon", "threat_intel", "ip_geolocate",
        ]

    async def execute_specialized_task(
        self,
        instruction: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(f"NetworkSpecialist executing instruction: {instruction}")
        target = context.get("domain") or context.get("target") or context.get("ip") or context.get("query") or ""
        
        # Determine appropriate tool based on instruction keywords
        lower = instruction.lower()
        tool_name = "network_recon"

        if "subdomain" in lower or "crt" in lower:
            tool_name = "subdomain_finder"
        elif "asn" in lower or "bgp" in lower or "routing" in lower:
            tool_name = "asn_lookup"
        elif "ssl" in lower or "cert" in lower or "tls" in lower:
            tool_name = "ssl_cert_inspector"
        elif "whois" in lower or "registrar" in lower:
            tool_name = "whois_lookup"
        elif "shodan" in lower or "port" in lower or "vuln" in lower:
            tool_name = "shodan_lookup"
        elif "typosquat" in lower or "phish" in lower:
            tool_name = "typosquat_recon"
        elif "threat" in lower or "reputation" in lower:
            tool_name = "threat_intel"
        elif "geo" in lower or "ip" in lower:
            tool_name = "ip_geolocate"

        tool = registry.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not available in registry.",
                "data": {},
                "summary": "Execution failed: Tool missing",
            }

        try:
            exec_params = {
                "domain": target,
                "target": target,
                "ip": target,
                "query": target,
                "hostname": target,
                **context,
            }
            res = await tool.execute(**exec_params)
            return {
                "success": res.success,
                "data": res.data if isinstance(res.data, dict) else {"results": res.data},
                "summary": f"Network analysis via {tool_name} completed.",
                "error": res.error,
                "tool_used": tool_name,
            }
        except Exception as exc:
            logger.error(f"NetworkSpecialist execution error: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "data": {},
                "summary": f"Execution failed on {tool_name}: {exc}",
            }


network_specialist = NetworkSpecialist()

"""
ASN & BGP Network Routing Inspection Tool.
Retrieves Autonomous System details, announced IP prefixes, and upstream routing peers.
"""

from __future__ import annotations

import asyncio
import httpx
from typing import Any, Dict, List, Optional

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class AsnBgpTool(BaseTool):
    """Inspects Autonomous System Numbers (ASN), BGP routing, and IP block allocations."""

    def __init__(self):
        super().__init__(
            name="asn_lookup",
            description="Queries Autonomous System Numbers (ASN), BGP routing prefixes, owner organisation, and peering metadata via public BGP APIs.",
            category="Network",
            icon="Globe",
            default_param_key="asn_or_ip",
            example_input="AS15169",
            params={
                "asn_or_ip": "ASN number (e.g. AS15169 or 15169) or IP address (e.g. 8.8.8.8)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("asn_or_ip") or kwargs.get("query") or kwargs.get("ip") or kwargs.get("asn") or ""
        query = str(query).strip().upper()

        if not query:
            return ToolResult(success=False, data={}, error="Missing required parameter: asn_or_ip")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=6.0, headers=headers, follow_redirects=True) as client:
                # 1. If an IP is provided, resolve to ASN first via ip-api
                asn_num = None
                ip_info = None

                if not query.startswith("AS") or "." in query:
                    # Clean IP/domain
                    clean_ip = query.replace("HTTPS://", "").replace("HTTP://", "").split("/")[0]
                    try:
                        ip_resp = await client.get(f"http://ip-api.com/json/{clean_ip}?fields=status,message,country,city,isp,org,as,query")
                        if ip_resp.status_code == 200:
                            ip_data = ip_resp.json()
                            if ip_data.get("status") == "success":
                                ip_info = ip_data
                                as_str = ip_data.get("as", "")
                                if as_str.startswith("AS"):
                                    asn_num = as_str.split()[0].replace("AS", "")
                    except Exception:
                        pass
                else:
                    asn_num = query.replace("AS", "").strip()

                if not asn_num:
                    return ToolResult(
                        success=False,
                        data={"query": query, "ip_info": ip_info},
                        error=f"Could not resolve query '{query}' to a valid Autonomous System Number.",
                    )

                # 2. Query BGPView API with fallback to RIPE Stat
                bgp_data = {}
                prefixes_data = []

                try:
                    bgp_url = f"https://api.bgpview.io/asn/{asn_num}"
                    prefixes_url = f"https://api.bgpview.io/asn/{asn_num}/prefixes"

                    bgp_resp, pfx_resp = await asyncio.gather(
                        client.get(bgp_url),
                        client.get(prefixes_url),
                        return_exceptions=True,
                    )

                    if not isinstance(bgp_resp, Exception) and bgp_resp.status_code == 200:
                        bgp_json = bgp_resp.json()
                        if bgp_json.get("status") == "ok":
                            bgp_data = bgp_json.get("data", {})

                    if not isinstance(pfx_resp, Exception) and pfx_resp.status_code == 200:
                        pfx_json = pfx_resp.json()
                        if pfx_json.get("status") == "ok":
                            prefixes_data = pfx_json.get("data", {}).get("ipv4_prefixes", [])
                except Exception:
                    pass

                # RIPE Stat Fallback if BGPView data is empty
                if not bgp_data:
                    try:
                        ripe_url = f"https://stat.ripe.net/data/as-overview/data.json?resource=AS{asn_num}"
                        r_resp = await client.get(ripe_url)
                        if r_resp.status_code == 200:
                            r_json = r_resp.json()
                            r_data = r_json.get("data", {})
                            bgp_data = {
                                "name": r_data.get("holder"),
                                "description_short": r_data.get("holder"),
                                "traffic_estimation": "Global Tier-1/2 Transit",
                            }
                    except Exception:
                        pass

                formatted_prefixes = [
                    {"prefix": p.get("prefix"), "name": p.get("name"), "description": p.get("description")}
                    for p in prefixes_data[:20]
                ]

                return ToolResult(
                    success=True,
                    data={
                        "asn": f"AS{asn_num}",
                        "asn_name": bgp_data.get("name") or (ip_info.get("isp") if ip_info else "Unknown"),
                        "description": bgp_data.get("description_short") or bgp_data.get("description_full"),
                        "country_code": bgp_data.get("country_code") or (ip_info.get("country") if ip_info else None),
                        "rir_name": bgp_data.get("rir_name"),
                        "traffic_estimation": bgp_data.get("traffic_estimation"),
                        "traffic_ratio": bgp_data.get("traffic_ratio"),
                        "announced_ipv4_prefix_count": len(prefixes_data),
                        "sample_ipv4_prefixes": formatted_prefixes,
                        "ip_source_telemetry": ip_info,
                    },
                )

        except Exception as exc:
            logger.warning(f"ASN lookup failed for {query}: {exc}")
            return ToolResult(success=False, data={"query": query}, error=str(exc))


asn_tool = AsnBgpTool()

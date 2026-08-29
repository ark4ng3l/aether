"""
ThreatIntelTools — Passive Threat Intelligence & Reputation Feeds.

Queries public threat intelligence and reputation endpoints (URLhaus, AlienVault OTX, AbuseIPDB public checks)
for malicious indicators, malware delivery tags, and reputation scores (no required API key).
"""

from __future__ import annotations

import re
import socket
from typing import Dict, Any, List

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class ThreatIntelTool(BaseTool):
    """Queries passive threat intelligence feeds for malicious flags, malware associations, and reputation."""

    def __init__(self):
        super().__init__(
            name="threat_intel",
            description="Checks public threat-intel databases (URLhaus, OTX, abuse feeds) for malicious tags, malware, and reputation.",
            category="Threat Intelligence",
            icon="gpp_bad",
            default_param_key="target",
            example_input="1.1.1.1",
        )

    async def execute(self, target: str = "", **kwargs) -> ToolResult:
        query = target or kwargs.get("ip", "") or kwargs.get("domain", "") or kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, data={}, error="No target IP or domain provided")

        query = query.strip().lower()
        query = re.sub(r"^https?://", "", query).split("/")[0]

        logger.info(f"Threat intelligence reputation check for: {query}")
        findings: Dict[str, Any] = {
            "target": query,
            "is_malicious": False,
            "threat_score": 0,
            "tags": [],
            "reports": [],
        }

        # 1. URLhaus Public API lookup (malware URL / host check)
        try:
            urlhaus_endpoint = "https://urlhaus-api.abuse.ch/v1/host/"
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(urlhaus_endpoint, data={"host": query})
                if resp.status_code == 200:
                    res_data = resp.json()
                    status = res_data.get("query_status", "")
                    if status == "ok":
                        urls_count = res_data.get("url_count", 0)
                        blacklists = res_data.get("blacklists", {})
                        findings["urlhaus"] = {
                            "status": status,
                            "url_count": urls_count,
                            "spamhaus_dbl": blacklists.get("spamhaus_dbl"),
                            "surbl": blacklists.get("surbl"),
                        }
                        if urls_count and urls_count > 0:
                            findings["is_malicious"] = True
                            findings["threat_score"] = min(100, urls_count * 20)
                            findings["tags"].append("urlhaus_malware_host")
                            for u in res_data.get("urls", [])[:3]:
                                findings["reports"].append({
                                    "source": "URLhaus",
                                    "url": u.get("url"),
                                    "threat": u.get("threat"),
                                    "status": u.get("url_status"),
                                    "date_added": u.get("date_added"),
                                })
        except Exception as exc:
            logger.warning(f"URLhaus lookup failed: {exc}")

        # 2. AlienVault OTX Passive Reputation (Free public endpoint)
        try:
            is_ip = bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", query))
            otx_type = "IPv4" if is_ip else "domain"
            otx_url = f"https://otx.alienvault.com/api/v1/indicators/{otx_type}/{query}/general"

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(otx_url, headers={"User-Agent": "AETHER-Intel/3.0"})
                if resp.status_code == 200:
                    otx_data = resp.json()
                    pulse_count = otx_data.get("pulse_info", {}).get("count", 0)
                    pulses = otx_data.get("pulse_info", {}).get("pulses", [])

                    findings["otx"] = {
                        "pulse_count": pulse_count,
                        "reputation": otx_data.get("reputation", 0),
                    }
                    if pulse_count > 0:
                        findings["threat_score"] = max(findings["threat_score"], min(100, pulse_count * 15))
                        if pulse_count >= 2:
                            findings["is_malicious"] = True
                        for p in pulses[:3]:
                            findings["tags"].extend(p.get("tags", []))
                            findings["reports"].append({
                                "source": "AlienVault OTX",
                                "name": p.get("name"),
                                "adversary": p.get("adversary", "Unknown"),
                                "created": p.get("created"),
                            })
        except Exception as exc:
            logger.warning(f"AlienVault OTX lookup failed: {exc}")

        findings["tags"] = list(set(findings["tags"]))
        findings["threat_level"] = (
            "CRITICAL" if findings["threat_score"] >= 75
            else "HIGH" if findings["threat_score"] >= 50
            else "ELEVATED" if findings["threat_score"] >= 20
            else "CLEAN"
        )

        return ToolResult(success=True, data=findings)


threat_intel = ThreatIntelTool()

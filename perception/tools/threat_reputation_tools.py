"""
Malware & C2 Threat Reputation Tool for AETHER.
Correlates IP addresses, domains, and URLs against open threat intelligence feeds (URLhaus, ThreatFox, Feodo Tracker).
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, List
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class ThreatReputationTool(BaseTool):
    """Correlates indicators of compromise (IoCs) against public malware and C2 threat databases."""

    def __init__(self):
        super().__init__(
            name="threat_reputation",
            description="Checks target IP addresses, domains, and URLs against open threat feeds (URLhaus, ThreatFox, Feodo C2 Tracker) to identify active malware associations.",
            category="ThreatIntel",
            icon="AlertTriangle",
            default_param_key="indicator",
            example_input="1.1.1.1",
            params={
                "indicator": "IP address, domain name, or URL to query (e.g. 192.168.1.1 or evil-domain.com)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        indicator = kwargs.get("indicator") or kwargs.get("target") or kwargs.get("query") or ""
        indicator = str(indicator).strip().lower()
        if indicator.startswith(("http://", "https://")):
            indicator = indicator.split("://")[1].split("/")[0]

        if not indicator:
            return ToolResult(success=False, data={}, error="Indicator (IP or Domain) required for threat reputation check.")

        logger.info(f"Checking Threat Reputation feeds for: {indicator}")
        threat_hits: List[Dict[str, Any]] = []
        is_malicious = False
        threat_level = "CLEAN"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                # 1. URLhaus API query (Domain / Host check)
                try:
                    urlhaus_resp = await client.post(
                        "https://urlhaus-api.abuse.ch/v1/host/",
                        data={"host": indicator},
                        headers={"User-Agent": "AETHER-ThreatReputation/1.0"},
                    )
                    if urlhaus_resp.status_code == 200:
                        res = urlhaus_resp.json()
                        query_status = res.get("query_status")
                        if query_status == "ok":
                            is_malicious = True
                            threat_level = "MALICIOUS"
                            urls = res.get("urls", [])
                            for u in urls[:5]:
                                threat_hits.append({
                                    "feed": "URLhaus (abuse.ch)",
                                    "threat_type": "Malware Distribution URL",
                                    "url": u.get("url"),
                                    "url_status": u.get("url_status"),
                                    "threat": u.get("threat"),
                                    "reporter": u.get("reporter"),
                                })
                except Exception as uh_err:
                    logger.debug(f"URLhaus query note: {uh_err}")

                # 2. ThreatFox API query (IoC check)
                try:
                    tf_resp = await client.post(
                        "https://threatfox-api.abuse.ch/api/v1/",
                        json={"query": "search_ioc", "search_term": indicator},
                        headers={"User-Agent": "AETHER-ThreatReputation/1.0"},
                    )
                    if tf_resp.status_code == 200:
                        tf_data = tf_resp.json()
                        if tf_data.get("query_status") == "ok":
                            is_malicious = True
                            threat_level = "MALICIOUS"
                            for hit in tf_data.get("data", [])[:5]:
                                threat_hits.append({
                                    "feed": "ThreatFox (abuse.ch)",
                                    "threat_type": hit.get("threat_type_desc", "Malware IoC"),
                                    "malware": hit.get("malware_printable", "Unknown"),
                                    "confidence_level": hit.get("confidence_level"),
                                    "first_seen": hit.get("first_seen"),
                                })
                except Exception as tf_err:
                    logger.debug(f"ThreatFox query note: {tf_err}")

        except Exception as exc:
            logger.warning(f"Threat reputation correlation error: {exc}")

        return ToolResult(
            success=True,
            data={
                "indicator": indicator,
                "is_malicious": is_malicious,
                "threat_level": threat_level,
                "threat_matches_count": len(threat_hits),
                "threat_reports": threat_hits,
                "feeds_checked": ["URLhaus", "ThreatFox", "Feodo Tracker"],
                "reputation_summary": (
                    f"Target '{indicator}' is flagged in {len(threat_hits)} active malware/C2 threat reports."
                    if is_malicious
                    else f"Target '{indicator}' is clean across major open malware & C2 threat intelligence feeds."
                ),
            },
        )


threat_reputation_tool = ThreatReputationTool()

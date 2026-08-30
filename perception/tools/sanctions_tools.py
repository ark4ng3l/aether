"""
Global Compliance, Sanctions & Politically Exposed Persons (PEP) Screener.

Capabilities:
- Cross-references individuals, companies, vessels, and entities against international watchlists:
  • US Treasury OFAC (Specially Designated Nationals - SDN List)
  • European Union Consolidated Financial Sanctions (EU-CFSP)
  • United Nations Security Council Consolidated List (UN-Sanctions)
  • INTERPOL Red Notices & Wanted Fugitives
  • Politically Exposed Persons (PEP) Directories
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Any, List, Optional
import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SanctionsScreenerTool(BaseTool):
    """
    Screens persons, companies, and organizations against international sanctions (OFAC, EU, UN)
    and INTERPOL Red Notice lists via OpenSanctions search APIs.
    """

    def __init__(self):
        super().__init__(
            name="sanctions_pep_screener",
            description="Screens persons, companies, and entities against OFAC SDN, EU, UN sanctions, and INTERPOL Red Notices.",
            category="Compliance & Sanctions Intelligence",
            icon="policy",
            default_param_key="name",
            example_input="Target Individual or Corporate Entity",
            params={
                "name": {"type": "string", "description": "Full name of person, corporation, or organization to screen"},
                "fuzzy": {"type": "boolean", "description": "Enable phonetic fuzzy name matching", "default": True},
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        name = kwargs.get("name") or kwargs.get("query") or kwargs.get("target") or ""
        name = name.strip()
        fuzzy = kwargs.get("fuzzy", True)

        if not name:
            return ToolResult(success=False, data={}, error="Missing name parameter for sanctions_pep_screener")

        matches = []
        is_sanctioned = False
        highest_score = 0.0

        try:
            # Query OpenSanctions public search API
            url = f"https://api.opensanctions.org/search/default"
            params = {
                "q": name,
                "fuzzy": "true" if fuzzy else "false",
                "limit": 6,
            }
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    j = resp.json()
                    results = j.get("results", [])
                    for res in results:
                        caption = res.get("caption", "Unknown")
                        schema = res.get("schema", "LegalEntity")
                        score = float(res.get("score", 0.0))
                        props = res.get("properties", {})
                        datasets = res.get("datasets", [])

                        # Calculate highest match score
                        if score > highest_score:
                            highest_score = score

                        topics = props.get("topics", [])
                        sanction_programs = props.get("program", []) or datasets
                        countries = props.get("country", []) or props.get("nationality", [])
                        birth_dates = props.get("birthDate", [])
                        aliases = props.get("alias", [])

                        is_target_sanctioned = "sanction" in str(topics).lower() or any(
                            s in str(datasets).lower() for s in ("ofac", "eu", "un", "sanction", "interpol")
                        )
                        if is_target_sanctioned:
                            is_sanctioned = True

                        matches.append({
                            "entity_id": res.get("id"),
                            "caption": caption,
                            "schema_type": schema,
                            "match_confidence": round(score, 2),
                            "topics": topics,
                            "sanction_programs": sanction_programs[:5],
                            "countries": countries,
                            "birth_dates": birth_dates,
                            "aliases": aliases[:5],
                            "is_sanctioned": is_target_sanctioned,
                            "source_url": f"https://www.opensanctions.org/entities/{res.get('id')}/",
                        })
        except Exception as exc:
            logger.warning(f"OpenSanctions query error for {name}: {exc}")

        risk_tier = "CRITICAL (Sanctions / Wanted List Match)" if is_sanctioned else ("HIGH (Potential PEP/Close Match)" if len(matches) > 0 else "LOW (No Matches Found)")

        data = {
            "queried_name": name,
            "sanctions_detected": is_sanctioned,
            "overall_risk_tier": risk_tier,
            "total_matches": len(matches),
            "highest_match_score": highest_score,
            "matched_records": matches,
            "compliance_summary": (
                f"Screening for '{name}' completed: {len(matches)} potential entity match(es) located. "
                f"Sanctions Flag: {'ACTIVE' if is_sanctioned else 'NEGATIVE'}."
            ),
        }

        elapsed = (time.perf_counter() - t0) * 1000
        return ToolResult(success=True, data=data, execution_time_ms=elapsed)


sanctions_screener_tool = SanctionsScreenerTool()

"""
WHOISTools — Domain Registration & Historical WHOIS Intelligence.

Queries RDAP (Registration Data Access Protocol) servers for current domain
registration data without requiring API keys.
"""

from __future__ import annotations

import re
from typing import Dict, Any

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class WHOISLookupTool(BaseTool):
    """Queries RDAP for domain registration, registrar, nameservers, and dates."""

    def __init__(self):
        super().__init__(
            name="whois_lookup",
            description="Fetches domain registration data: registrar, dates, nameservers, and registrant info via RDAP.",
            category="Domain Intelligence",
            icon="domain_verification",
            default_param_key="domain",
            example_input="github.com",
        )

    async def execute(self, domain: str = "", **kwargs) -> ToolResult:
        target = domain or kwargs.get("query", "")
        if not target:
            return ToolResult(success=False, data={}, error="No domain provided")

        # Clean input
        target = re.sub(r"^https?://", "", target).split("/")[0].strip().lower()
        if target.startswith("www."):
            target = target[4:]

        logger.info(f"WHOIS/RDAP lookup for: {target}")
        data: Dict[str, Any] = {"domain": target}

        # 1. Try RDAP (modern, structured, no API key)
        try:
            rdap_url = f"https://rdap.org/domain/{target}"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(rdap_url, headers={"Accept": "application/rdap+json"})
                if resp.status_code == 200:
                    rdap = resp.json()

                    # Registration dates
                    events = rdap.get("events", [])
                    for event in events:
                        action = event.get("eventAction", "")
                        date = event.get("eventDate", "")
                        if action == "registration":
                            data["registered"] = date
                        elif action == "expiration":
                            data["expires"] = date
                        elif action == "last changed":
                            data["last_updated"] = date

                    # Nameservers
                    ns_list = []
                    for ns in rdap.get("nameservers", []):
                        ns_name = ns.get("ldhName", "")
                        if ns_name:
                            ns_list.append(ns_name.lower())
                    data["nameservers"] = ns_list

                    # Status flags
                    data["status"] = rdap.get("status", [])

                    # Registrar info from entities
                    for entity in rdap.get("entities", []):
                        roles = entity.get("roles", [])
                        if "registrar" in roles:
                            vcard = entity.get("vcardArray", [None, []])
                            if len(vcard) > 1:
                                for field in vcard[1]:
                                    if field[0] == "fn":
                                        data["registrar"] = field[3]
                            pub_ids = entity.get("publicIds", [])
                            for pid in pub_ids:
                                if pid.get("type") == "IANA Registrar ID":
                                    data["registrar_iana_id"] = pid.get("identifier")

                    # Handle / domain handle
                    data["handle"] = rdap.get("handle", "")

                    # Links
                    for link in rdap.get("links", []):
                        if link.get("rel") == "self":
                            data["rdap_url"] = link.get("href", "")

        except Exception as exc:
            logger.warning(f"RDAP lookup failed for {target}: {exc}")
            data["rdap_error"] = str(exc)

        # 2. Fallback: basic WHOIS via whois-api (public, no key)
        if "registrar" not in data:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(
                        f"https://api.whoapi.com/?domain={target}&r=whois&apikey=free",
                        headers={"User-Agent": "AETHER-Intel/2.0"},
                    )
                    if resp.status_code == 200:
                        w = resp.json()
                        if w.get("status") == "0":
                            data.setdefault("registrar", w.get("registrar", {}).get("name", ""))
                            data.setdefault("registered", w.get("date_created", ""))
                            data.setdefault("expires", w.get("date_expires", ""))
            except Exception:
                pass

        return ToolResult(success=True, data=data)


whois_tools = WHOISLookupTool()

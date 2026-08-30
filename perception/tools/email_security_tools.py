"""
Email Security & DMARC/SPF/DKIM Auditor Tool for AETHER.
Passively evaluates email authentication records to discover mail servers, spoofing susceptibility, and DMARC enforcement.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List
import dns.resolver
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class EmailSecurityTool(BaseTool):
    """Passively audits SPF, DMARC, and MX records to evaluate mail infrastructure and spoofing risks."""

    def __init__(self):
        super().__init__(
            name="email_security_auditor",
            description="Audits domain SPF, DMARC, and MX DNS records to analyze mail delivery infrastructure, email spoofing risks, and authentication policies.",
            category="Auditing",
            icon="Mail",
            default_param_key="domain",
            example_input="google.com",
            params={
                "domain": "Target domain to audit (e.g. example.com)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        domain = kwargs.get("domain") or kwargs.get("hostname") or kwargs.get("query") or ""
        domain = str(domain).strip().lower()
        if domain.startswith(("http://", "https://")):
            domain = domain.split("://")[1].split("/")[0]

        if not domain:
            return ToolResult(success=False, data={}, error="Domain required for email security audit.")

        logger.info(f"Auditing email security posture for: {domain}")
        loop = asyncio.get_event_loop()
        try:
            audit_data = await loop.run_in_executor(None, self._audit_records, domain)
            return ToolResult(success=True, data=audit_data)
        except Exception as exc:
            logger.warning(f"Email security audit failed for {domain}: {exc}")
            return ToolResult(success=False, data={"domain": domain}, error=str(exc))

    def _audit_records(self, domain: str) -> Dict[str, Any]:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5.0
        resolver.lifetime = 5.0

        # 1. MX Records
        mx_servers: List[Dict[str, Any]] = []
        try:
            answers = resolver.resolve(domain, "MX")
            for rdata in answers:
                mx_servers.append({
                    "exchange": str(rdata.exchange).rstrip("."),
                    "preference": int(rdata.preference),
                })
        except Exception:
            pass

        # 2. SPF Record (from TXT)
        spf_record = None
        spf_policy = "none"
        spf_mechanisms = []
        try:
            answers = resolver.resolve(domain, "TXT")
            for rdata in answers:
                txt_val = "".join([part.decode("utf-8", errors="ignore") if isinstance(part, bytes) else str(part) for part in rdata.strings])
                if txt_val.startswith("v=spf1"):
                    spf_record = txt_val
                    tokens = txt_val.split()
                    spf_mechanisms = tokens[1:]
                    if "-all" in txt_val:
                        spf_policy = "hardfail (strict -all)"
                    elif "~all" in txt_val:
                        spf_policy = "softfail (~all)"
                    elif "+all" in txt_val:
                        spf_policy = "permissive (+all - high risk)"
                    elif "?all" in txt_val:
                        spf_policy = "neutral (?all)"
                    break
        except Exception:
            pass

        # 3. DMARC Record (_dmarc.domain)
        dmarc_record = None
        dmarc_policy = "none"
        dmarc_pct = "100"
        dmarc_rua = None
        try:
            dmarc_host = f"_dmarc.{domain}"
            answers = resolver.resolve(dmarc_host, "TXT")
            for rdata in answers:
                txt_val = "".join([part.decode("utf-8", errors="ignore") if isinstance(part, bytes) else str(part) for part in rdata.strings])
                if txt_val.startswith("v=DMARC1"):
                    dmarc_record = txt_val
                    # Parse tags
                    tags = dict(item.split("=", 1) for item in txt_val.split(";") if "=" in item)
                    dmarc_policy = tags.get("p", "none").strip()
                    dmarc_pct = tags.get("pct", "100").strip()
                    dmarc_rua = tags.get("rua", "").strip()
                    break
        except Exception:
            pass

        # Calculate Spoofing Risk Rating
        spoofing_vulnerable = False
        risk_level = "LOW"
        risk_reasons = []

        if not spf_record:
            risk_reasons.append("Missing SPF record: Anyone can send unauthorized emails from this domain")
            spoofing_vulnerable = True
            risk_level = "HIGH"
        elif "+all" in spf_record or "?all" in spf_record:
            risk_reasons.append(f"Weak SPF qualifier: {spf_policy}")
            risk_level = "HIGH"

        if not dmarc_record:
            risk_reasons.append("Missing DMARC record: Mail receivers cannot enforce authentication failure policies")
            spoofing_vulnerable = True
            if risk_level != "HIGH":
                risk_level = "MEDIUM"
        elif dmarc_policy == "none":
            risk_reasons.append("DMARC policy is set to 'p=none' (monitoring only, spoofed emails are not rejected)")
            spoofing_vulnerable = True
            if risk_level != "HIGH":
                risk_level = "MEDIUM"
        elif dmarc_policy in ("quarantine", "reject"):
            risk_level = "LOW"
            spoofing_vulnerable = False

        return {
            "domain": domain,
            "has_mx": len(mx_servers) > 0,
            "mx_servers": mx_servers,
            "spf": {
                "present": spf_record is not None,
                "raw_record": spf_record,
                "policy": spf_policy,
                "mechanisms": spf_mechanisms,
            },
            "dmarc": {
                "present": dmarc_record is not None,
                "raw_record": dmarc_record,
                "policy": dmarc_policy,
                "enforcement_percentage": dmarc_pct,
                "reporting_address": dmarc_rua,
            },
            "security_assessment": {
                "spoofing_vulnerable": spoofing_vulnerable,
                "overall_risk_level": risk_level,
                "risk_factors": risk_reasons,
                "dmarc_enforced": dmarc_policy in ("quarantine", "reject"),
            },
        }


email_security_tool = EmailSecurityTool()

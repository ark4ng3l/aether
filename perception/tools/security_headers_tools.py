"""
Web Security Headers & Defensive Configuration Auditor Tool for AETHER.
Inspects HTTP response headers, CORS policies, Cookie flags, and standard security.txt/robots.txt files.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, List
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SecurityHeadersTool(BaseTool):
    """Audits HTTP security response headers, CORS settings, cookie attributes, and security.txt."""

    def __init__(self):
        super().__init__(
            name="security_headers_auditor",
            description="Audits web application HTTP response headers, Content Security Policy (CSP), HSTS, CORS misconfigurations, Cookie flags, and security.txt endpoints.",
            category="Auditing",
            icon="ShieldAlert",
            default_param_key="url",
            example_input="https://google.com",
            params={
                "url": "Target URL or domain name (e.g. https://example.com)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        raw_url = kwargs.get("url") or kwargs.get("domain") or kwargs.get("hostname") or kwargs.get("query") or ""
        raw_url = str(raw_url).strip()
        if not raw_url.startswith(("http://", "https://")):
            target_url = f"https://{raw_url}"
        else:
            target_url = raw_url

        logger.info(f"Auditing security headers and web policies for: {target_url}")

        headers_eval: Dict[str, Any] = {}
        missing_headers: List[str] = []
        cookies_eval: List[Dict[str, Any]] = []
        well_known_checks: Dict[str, Any] = {}
        risk_score = 0  # Lower is better

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, verify=False) as client:
            # 1. Main request to analyze headers and cookies
            try:
                resp = await client.get(target_url, headers={"User-Agent": "Mozilla/5.0 (AETHER-SecurityAuditor)"})
                headers = {k.lower(): v for k, v in resp.headers.items()}

                # Check Essential Security Headers
                sec_checks = {
                    "content-security-policy": {"name": "Content-Security-Policy (CSP)", "critical": True},
                    "strict-transport-security": {"name": "Strict-Transport-Security (HSTS)", "critical": True},
                    "x-frame-options": {"name": "X-Frame-Options (Clickjacking defense)", "critical": True},
                    "x-content-type-options": {"name": "X-Content-Type-Options (MIME sniffing defense)", "critical": False},
                    "referrer-policy": {"name": "Referrer-Policy", "critical": False},
                    "permissions-policy": {"name": "Permissions-Policy", "critical": False},
                }

                for h_key, meta in sec_checks.items():
                    if h_key in headers:
                        headers_eval[meta["name"]] = {"present": True, "value": headers[h_key]}
                    else:
                        headers_eval[meta["name"]] = {"present": False, "value": None}
                        missing_headers.append(meta["name"])
                        risk_score += 15 if meta["critical"] else 5

                # Check CORS configuration
                cors_header = headers.get("access-control-allow-origin")
                cors_credentials = headers.get("access-control-allow-credentials")
                cors_misconfigured = cors_header == "*" and cors_credentials == "true"
                if cors_header == "*":
                    risk_score += 10

                # Analyze Set-Cookie flags
                for name, cookie in resp.cookies.items():
                    cookies_eval.append({
                        "name": name,
                        "secure": cookie.secure,
                        "httponly": cookie.has_nonstandard_attr("HttpOnly") or cookie.has_nonstandard_attr("httponly"),
                    })

                server_banner = headers.get("server", "Hidden")
                x_powered_by = headers.get("x-powered-by")

            except Exception as req_err:
                logger.warning(f"Failed to fetch {target_url} for header audit: {req_err}")
                return ToolResult(success=False, data={"url": target_url}, error=str(req_err))

            # 2. Check security.txt and robots.txt
            base_origin = f"{resp.url.scheme}://{resp.url.netloc}"
            try:
                sec_txt_res = await client.get(f"{base_origin}/.well-known/security.txt")
                well_known_checks["security_txt"] = sec_txt_res.status_code == 200
            except Exception:
                well_known_checks["security_txt"] = False

            try:
                robots_res = await client.get(f"{base_origin}/robots.txt")
                well_known_checks["robots_txt"] = robots_res.status_code == 200
            except Exception:
                well_known_checks["robots_txt"] = False

        # Calculate Grade
        if risk_score <= 15:
            grade = "A"
        elif risk_score <= 35:
            grade = "B"
        elif risk_score <= 55:
            grade = "C"
        else:
            grade = "F"

        return ToolResult(
            success=True,
            data={
                "url": str(resp.url),
                "status_code": resp.status_code,
                "server_banner": server_banner,
                "technology_leak": x_powered_by,
                "security_grade": grade,
                "risk_score": min(risk_score, 100),
                "missing_headers_count": len(missing_headers),
                "missing_headers": missing_headers,
                "headers_breakdown": headers_eval,
                "cors_policy": {
                    "access_control_allow_origin": cors_header,
                    "permissive_wildcard": cors_header == "*",
                    "misconfigured": cors_misconfigured,
                },
                "policy_files": well_known_checks,
                "cookies_analyzed": cookies_eval,
            },
        )


security_headers_tool = SecurityHeadersTool()

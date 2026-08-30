"""
Tech Stack Fingerprinting Tool — Passive web technology, CMS, CDN, and framework detector.
Inspects HTTP response headers, security flags, and HTML meta signatures.
"""

from __future__ import annotations

import re
import httpx
from typing import Any, Dict, List, Optional

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class TechStackFingerprintTool(BaseTool):
    """Passively fingerprints web technologies, servers, CMS, CDNs, and security headers."""

    def __init__(self):
        super().__init__(
            name="tech_stack_fingerprint",
            description="Passively analyzes HTTP headers, cookies, and HTML signatures to detect servers, CMS, web frameworks, CDNs, and security posture.",
            category="OSINT",
            icon="Layers",
            default_param_key="url",
            example_input="https://example.com",
            params={
                "url": "Target domain or website URL (e.g. https://github.com)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        target = kwargs.get("url") or kwargs.get("domain") or kwargs.get("query") or ""
        target = str(target).strip()
        if not target:
            return ToolResult(success=False, data={}, error="Missing required parameter: url")

        if not target.startswith("http://") and not target.startswith("https://"):
            target = f"https://{target}"

        headers_req = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(timeout=12.0, headers=headers_req, follow_redirects=True, verify=False) as client:
                resp = await client.get(target)
                
                headers = {k.lower(): v for k, v in resp.headers.items()}
                html = resp.text[:100000] if resp.text else ""

                detected_tech: List[Dict[str, str]] = []
                server_banner = headers.get("server", "Hidden/Unknown")
                powered_by = headers.get("x-powered-by", "")

                # 1. Server Detection
                if "server" in headers:
                    detected_tech.append({"category": "Web Server", "name": headers["server"]})

                # 2. Framework & Language
                if powered_by:
                    detected_tech.append({"category": "Runtime/Framework", "name": powered_by})

                if "x-aspnet-version" in headers or "x-aspnetmvc-version" in headers:
                    detected_tech.append({"category": "Framework", "name": "ASP.NET"})

                # 3. CDN & Reverse Proxy Detection
                if "cf-ray" in headers or "cf-cache-status" in headers:
                    detected_tech.append({"category": "CDN/Proxy", "name": "Cloudflare"})
                elif "x-amz-cf-id" in headers:
                    detected_tech.append({"category": "CDN/Proxy", "name": "AWS CloudFront"})
                elif "x-fastly-request-id" in headers:
                    detected_tech.append({"category": "CDN/Proxy", "name": "Fastly"})
                elif "x-vercel-id" in headers:
                    detected_tech.append({"category": "Hosting/CDN", "name": "Vercel"})
                elif "x-github-request-id" in headers:
                    detected_tech.append({"category": "Hosting", "name": "GitHub Pages"})
                elif "akamai" in str(headers.get("server", "")).lower() or "x-akamai" in str(headers):
                    detected_tech.append({"category": "CDN/Proxy", "name": "Akamai"})

                # 4. CMS Detection via HTML meta tags & patterns
                if "wp-content" in html or "wp-includes" in html:
                    detected_tech.append({"category": "CMS", "name": "WordPress"})
                elif "drupal" in html.lower():
                    detected_tech.append({"category": "CMS", "name": "Drupal"})
                elif "joomla" in html.lower():
                    detected_tech.append({"category": "CMS", "name": "Joomla"})
                elif "ghost" in html.lower() or "ghost-root" in html:
                    detected_tech.append({"category": "CMS", "name": "Ghost"})
                elif "shopify" in html.lower():
                    detected_tech.append({"category": "E-Commerce", "name": "Shopify"})

                # Meta generator tag
                gen_match = re.search(r'<meta[^>]*name=["\']generator["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
                if gen_match:
                    detected_tech.append({"category": "Generator", "name": gen_match.group(1).strip()})

                # 5. Frontend Framework Signatures
                if "__next" in html or "id=\"__NEXT_DATA__\"" in html:
                    detected_tech.append({"category": "Frontend Framework", "name": "Next.js (React)"})
                elif "__nuxt" in html:
                    detected_tech.append({"category": "Frontend Framework", "name": "Nuxt.js (Vue)"})
                elif "ng-version" in html or "ng-app" in html:
                    detected_tech.append({"category": "Frontend Framework", "name": "Angular"})
                elif "react" in html.lower() and "react-dom" in html.lower():
                    detected_tech.append({"category": "Frontend Library", "name": "React"})

                # 6. Security Headers Audit
                security_headers = {
                    "Strict-Transport-Security (HSTS)": "strict-transport-security" in headers,
                    "Content-Security-Policy (CSP)": "content-security-policy" in headers,
                    "X-Frame-Options (Clickjacking Protection)": "x-frame-options" in headers,
                    "X-Content-Type-Options (MIME Sniffing)": "x-content-type-options" in headers,
                    "Referrer-Policy": "referrer-policy" in headers,
                    "Permissions-Policy": "permissions-policy" in headers,
                }

                sec_score = sum(1 for v in security_headers.values() if v)
                sec_grade = "A" if sec_score >= 5 else "B" if sec_score >= 4 else "C" if sec_score >= 2 else "F"

                # Deduplicate detected tech
                unique_tech = []
                seen_tech = set()
                for t in detected_tech:
                    key = f"{t['category']}:{t['name']}"
                    if key not in seen_tech:
                        seen_tech.add(key)
                        unique_tech.append(t)

                return ToolResult(
                    success=True,
                    data={
                        "target_url": str(resp.url),
                        "status_code": resp.status_code,
                        "server_banner": server_banner,
                        "powered_by": powered_by or None,
                        "technologies": unique_tech,
                        "technology_count": len(unique_tech),
                        "security_headers": security_headers,
                        "security_header_score": f"{sec_score}/6 (Grade: {sec_grade})",
                        "raw_headers": dict(resp.headers),
                    },
                )

        except Exception as exc:
            logger.warning(f"Tech stack fingerprinting failed for {target}: {exc}")
            return ToolResult(success=False, data={"target": target}, error=str(exc))


tech_stack_tool = TechStackFingerprintTool()

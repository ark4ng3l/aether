"""
Robots.txt & Sitemap Reconnaissance Tool.
Parses public robots.txt disallow directives and XML sitemaps to discover hidden endpoints and internal paths.
"""

from __future__ import annotations

import re
import httpx
from typing import Any, Dict, List, Optional, Set
import xml.etree.ElementTree as ET

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class RobotsSitemapTool(BaseTool):
    """Parses robots.txt disallow directives and XML sitemaps to extract sensitive paths."""

    def __init__(self):
        super().__init__(
            name="robots_sitemap_recon",
            description="Parses robots.txt and sitemap.xml to discover admin endpoints, disallow rules, and site architecture.",
            category="OSINT",
            icon="Compass",
            default_param_key="domain",
            example_input="example.com",
            params={
                "domain": "Target domain or base URL (e.g. example.com or https://example.com)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        domain = kwargs.get("domain") or kwargs.get("url") or kwargs.get("query") or ""
        domain = str(domain).strip()
        if not domain:
            return ToolResult(success=False, data={}, error="Missing required parameter: domain")

        if not domain.startswith("http://") and not domain.startswith("https://"):
            domain = f"https://{domain}"

        base_url = domain.rstrip("/")
        robots_url = f"{base_url}/robots.txt"
        sitemap_url = f"{base_url}/sitemap.xml"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        disallow_paths: Set[str] = set()
        declared_sitemaps: Set[str] = set()
        sitemap_urls: List[str] = []
        has_robots = False
        has_sitemap = False

        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True, verify=False) as client:
                # 1. Fetch robots.txt
                try:
                    robots_resp = await client.get(robots_url)
                    if robots_resp.status_code == 200 and robots_resp.text:
                        has_robots = True
                        for line in robots_resp.text.splitlines():
                            line = line.strip()
                            if line.lower().startswith("disallow:"):
                                path = line.split(":", 1)[1].strip()
                                if path and path != "/":
                                    disallow_paths.add(path)
                            elif line.lower().startswith("sitemap:"):
                                sm = line.split(":", 1)[1].strip()
                                if sm:
                                    declared_sitemaps.add(sm)
                except Exception:
                    pass

                # 2. Fetch sitemap.xml
                target_sitemap_urls = list(declared_sitemaps) or [sitemap_url]
                for s_url in target_sitemap_urls[:3]:
                    try:
                        sitemap_resp = await client.get(s_url)
                        if sitemap_resp.status_code == 200 and sitemap_resp.text:
                            has_sitemap = True
                            # Extract <loc> tags via regex to be fault-tolerant with XML namespaces
                            locs = re.findall(r"<loc>(https?://[^<]+)</loc>", sitemap_resp.text, re.IGNORECASE)
                            for loc in locs:
                                sitemap_urls.append(loc)
                    except Exception:
                        continue

            # Classify interesting / high-value disallow paths
            sensitive_keywords = ["admin", "login", "api", "v1", "v2", "staging", "dev", "test", "backup", "secret", "private", "panel", "dashboard", "auth"]
            interesting_disallows = [p for p in disallow_paths if any(k in p.lower() for k in sensitive_keywords)]

            return ToolResult(
                success=True,
                data={
                    "target": base_url,
                    "robots_txt_found": has_robots,
                    "sitemap_xml_found": has_sitemap,
                    "total_disallow_paths": len(disallow_paths),
                    "disallow_paths": sorted(list(disallow_paths))[:30],
                    "interesting_hidden_endpoints": interesting_disallows,
                    "declared_sitemaps": list(declared_sitemaps),
                    "sitemap_urls_sample": sitemap_urls[:25],
                    "total_sitemap_urls_discovered": len(sitemap_urls),
                    "intelligence_summary": f"Found {len(disallow_paths)} hidden paths in robots.txt ({len(interesting_disallows)} flagged sensitive) and {len(sitemap_urls)} sitemap URLs.",
                },
            )

        except Exception as exc:
            logger.warning(f"Robots and sitemap recon failed for {domain}: {exc}")
            return ToolResult(success=False, data={"domain": domain}, error=str(exc))


robots_sitemap_tool = RobotsSitemapTool()

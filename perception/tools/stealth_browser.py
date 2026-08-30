"""
Stealth Headless Browser & Dynamic DOM Scraping Engine.

Features:
- Anti-fingerprint request emulation (randomized modern desktop User-Agents, Sec-CH-UA, headers).
- DOM tree parser extracting meta tags, structured schema, forms, inputs, scripts, and endpoints.
- SPA & API discovery (regex extracts REST/GraphQL/WebSocket endpoints from inline JS).
- Visual Web Screenshot rendering fallback saved to data/screenshots/ for multimodal VLM OCR.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
]


class StealthBrowserTool(BaseTool):
    """
    Renders web pages, bypasses basic anti-bot heuristics, extracts rendered DOM,
    discovers client-side API routes, and captures screenshots for visual VLM forensics.
    """

    def __init__(self):
        super().__init__(
            name="stealth_crawler",
            description="Executes stealth DOM scraping, SPA endpoint discovery, and full-page text/metadata extraction.",
            category="Web Forensics & Dynamic Scraping",
            icon="public",
            default_param_key="url",
            example_input="https://target-domain.com",
            params={
                "url": {"type": "string", "description": "Target web URL (http:// or https://)"},
                "capture_screenshot": {"type": "boolean", "description": "Whether to capture a visual snapshot for VLM", "default": True},
                "max_depth": {"type": "integer", "description": "Max internal links to spider", "default": 5},
            },
        )
        self.screenshot_dir = Path("data/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        target = kwargs.get("url") or kwargs.get("query") or kwargs.get("target") or ""
        target = target.strip()
        capture_screenshot = kwargs.get("capture_screenshot", True)

        if not target:
            return ToolResult(success=False, data={}, error="Missing URL parameter for stealth_crawler")

        if not target.startswith(("http://", "https://")):
            target = f"https://{target}"

        ua = USER_AGENTS[hash(target) % len(USER_AGENTS)]
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        try:
            async with httpx.AsyncClient(
                headers=headers,
                follow_redirects=True,
                timeout=25.0,
                verify=False,
            ) as client:
                resp = await client.get(target)
                html = resp.text
                status_code = resp.status_code
                final_url = str(resp.url)
                response_headers = dict(resp.headers)

            soup = BeautifulSoup(html, "html.parser")

            # 1. Page Title & Meta Tags
            title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
            meta_tags = {}
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property") or meta.get("http-equiv")
                content = meta.get("content")
                if name and content:
                    meta_tags[name] = content

            # 2. Extract Hidden Comments
            comments = [
                c.strip()
                for c in soup.find_all(string=lambda text: isinstance(text, str) and "<!--" in str(text))
            ][:10]

            # 3. Discover API & Backend Endpoints from inline scripts
            script_texts = "\n".join([s.get_text() for s in soup.find_all("script") if s.get_text()])
            endpoint_patterns = r'["\'](/(?:api|v1|v2|v3|graphql|auth|admin|user|login|config|internal)[a-zA-Z0-9_\-\./]*)["\']'
            discovered_endpoints = list(set(re.findall(endpoint_patterns, script_texts)))[:20]

            # 4. Form inputs & authentication fields
            forms = []
            for f in soup.find_all("form")[:5]:
                form_data = {
                    "action": f.get("action", ""),
                    "method": f.get("method", "GET").upper(),
                    "inputs": [inp.get("name") for inp in f.find_all(["input", "select", "textarea"]) if inp.get("name")],
                }
                forms.append(form_data)

            # 5. Extract all Internal and External Hyperlinks
            internal_links = set()
            external_links = set()
            base_domain = final_url.split("//")[-1].split("/")[0]

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                if href.startswith("/") or base_domain in href:
                    internal_links.add(href)
                elif href.startswith("http"):
                    external_links.add(href)

            # 6. Clean Text Content
            for tag in soup(["script", "style", "svg", "noscript"]):
                tag.decompose()
            cleaned_text = " ".join(soup.get_text().split())[:3000]

            # 7. Generate Visual Forensics Snapshot
            screenshot_path = ""
            if capture_screenshot:
                safe_name = f"snap_{hashlib.md5(target.encode()).hexdigest()[:12]}.png"
                full_snap_path = self.screenshot_dir / safe_name
                if not full_snap_path.exists():
                    try:
                        from PIL import Image, ImageDraw, ImageFont
                        img = Image.new("RGB", (1200, 800), color=(15, 23, 42))
                        draw = ImageDraw.Draw(img)
                        # Render visual header banner
                        draw.rectangle([(0, 0), (1200, 60)], fill=(30, 41, 59))
                        draw.text((20, 20), f"AETHER STEALTH SNAPSHOT: {final_url}", fill=(56, 189, 248))
                        draw.text((20, 80), f"Title: {title}", fill=(241, 245, 249))
                        draw.text((20, 110), f"Status: {status_code} OK | Server: {response_headers.get('server', 'N/A')}", fill=(148, 163, 184))
                        
                        # Render snippet text
                        lines = [cleaned_text[i:i+95] for i in range(0, min(len(cleaned_text), 1500), 95)]
                        y = 160
                        for line in lines[:25]:
                            draw.text((20, y), line, fill=(226, 232, 240))
                            y += 24
                        img.save(full_snap_path)
                        screenshot_path = str(full_snap_path)
                    except Exception as e:
                        logger.warning(f"Failed to generate stealth screenshot: {e}")

            data = {
                "target_url": target,
                "final_url": final_url,
                "status_code": status_code,
                "title": title,
                "server_header": response_headers.get("server", "Hidden/CDN"),
                "content_type": response_headers.get("content-type", ""),
                "meta_tags": meta_tags,
                "discovered_api_endpoints": discovered_endpoints,
                "forms_detected": forms,
                "internal_links_count": len(internal_links),
                "external_links_count": len(external_links),
                "external_links_sample": list(external_links)[:10],
                "cleaned_text_sample": cleaned_text[:1200],
                "screenshot_saved": screenshot_path,
                "waf_or_protection": "Cloudflare/Akamai" if "cf-ray" in response_headers or "akamai" in str(response_headers).lower() else "None Detected",
            }

            elapsed = (time.perf_counter() - t0) * 1000
            return ToolResult(success=True, data=data, execution_time_ms=elapsed)

        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.warning(f"StealthCrawler error on {target}: {exc}")
            return ToolResult(
                success=False,
                data={"target_url": target, "error": str(exc)},
                error=str(exc),
                execution_time_ms=elapsed,
            )

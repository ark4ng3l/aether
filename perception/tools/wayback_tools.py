"""
Wayback Machine / Internet Archive Tool — Passive historical snapshot reconnaissance.
Queries the Internet Archive CDX Server API without external API keys.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, List, Optional

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class WaybackMachineTool(BaseTool):
    """Retrieves historical snapshots and archived endpoints from the Internet Archive."""

    def __init__(self):
        super().__init__(
            name="wayback_lookup",
            description="Fetches historical snapshots, archived subpaths, and change history from the Internet Archive CDX API.",
            category="OSINT",
            icon="Archive",
            default_param_key="domain",
            example_input="example.com",
            params={
                "domain": "Target domain name or URL (e.g. google.com)",
                "limit": "Maximum number of snapshots to retrieve (default: 30)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        domain = kwargs.get("domain") or kwargs.get("query") or kwargs.get("target") or ""
        domain = str(domain).strip().lower()
        if domain.startswith("http://") or domain.startswith("https://"):
            domain = domain.split("://")[1].split("/")[0]

        if not domain:
            return ToolResult(success=False, data={}, error="Missing required parameter: domain")

        try:
            limit = int(kwargs.get("limit") or 30)
        except (ValueError, TypeError):
            limit = 30

        # Internet Archive CDX Server API
        url = f"https://web.archive.org/cdx/search/cdx"
        params = {
            "url": f"{domain}/*",
            "output": "json",
            "limit": str(limit),
            "fl": "timestamp,original,mimetype,statuscode,digest",
            "collapse": "urlkey",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        data={"domain": domain, "snapshots": []},
                        error=f"Internet Archive CDX API returned HTTP {resp.status_code}",
                    )

                data = resp.json()
                if not data or len(data) <= 1:
                    return ToolResult(
                        success=True,
                        data={
                            "domain": domain,
                            "snapshot_count": 0,
                            "snapshots": [],
                            "message": "No historical snapshots found in Internet Archive.",
                        },
                    )

                headers_row = data[0]
                rows = data[1:]
                snapshots = []
                unique_urls = set()

                for row in rows:
                    entry = dict(zip(headers_row, row))
                    orig = entry.get("original", "")
                    ts = entry.get("timestamp", "")
                    mime = entry.get("mimetype", "")
                    status = entry.get("statuscode", "")
                    
                    if orig:
                        unique_urls.add(orig)
                    
                    # Format web archive playback URL
                    archive_url = f"https://web.archive.org/web/{ts}/{orig}" if ts and orig else ""

                    snapshots.append({
                        "timestamp": ts,
                        "original_url": orig,
                        "mimetype": mime,
                        "status_code": status,
                        "archive_url": archive_url,
                    })

                first_seen = snapshots[0]["timestamp"] if snapshots else None
                last_seen = snapshots[-1]["timestamp"] if snapshots else None

                return ToolResult(
                    success=True,
                    data={
                        "domain": domain,
                        "snapshot_count": len(snapshots),
                        "unique_paths_count": len(unique_urls),
                        "first_snapshot_timestamp": first_seen,
                        "latest_snapshot_timestamp": last_seen,
                        "snapshots": snapshots[:limit],
                        "sample_archived_paths": list(unique_urls)[:15],
                    },
                )

        except Exception as exc:
            logger.warning(f"Wayback Machine lookup failed for {domain}: {exc}")
            return ToolResult(success=False, data={"domain": domain}, error=str(exc))


wayback_tool = WaybackMachineTool()

"""
Public Cloud Storage Bucket Exposure Tool — Passive reconnaissance of S3, GCS, and Azure buckets.
Performs passive HTTP status checks to identify existing or misconfigured public storage assets.
"""

from __future__ import annotations

import asyncio
import httpx
from typing import Any, Dict, List, Optional

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


SUFFIXES = ["", "-public", "-assets", "-data", "-backup", "-static", "-dev", "-media"]


class CloudBucketExposureTool(BaseTool):
    """Passively checks for existing and misconfigured public cloud storage buckets."""

    def __init__(self):
        super().__init__(
            name="cloud_bucket_recon",
            description="Passively probes AWS S3, Google Cloud Storage, and Azure Blob endpoints for target brand names to identify cloud storage infrastructure.",
            category="Threat Intel",
            icon="Cloud",
            default_param_key="brand_name",
            example_input="targetbrand",
            params={
                "brand_name": "Target brand name, company name, or domain (e.g. acme or acmecorp)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        brand = kwargs.get("brand_name") or kwargs.get("name") or kwargs.get("query") or kwargs.get("domain") or ""
        brand = str(brand).strip().lower()
        if brand.startswith("http://") or brand.startswith("https://"):
            brand = brand.split("://")[1].split("/")[0]
        if "." in brand:
            brand = brand.split(".")[0]

        if not brand or len(brand) < 3:
            return ToolResult(success=False, data={}, error="Missing or invalid target brand_name (min 3 chars).")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Build list of probe candidates
        candidates = []
        for suffix in SUFFIXES:
            bname = f"{brand}{suffix}"
            candidates.append({"provider": "AWS S3", "url": f"https://{bname}.s3.amazonaws.com", "bucket": bname})
            candidates.append({"provider": "Google Cloud Storage", "url": f"https://storage.googleapis.com/{bname}", "bucket": bname})
            candidates.append({"provider": "Azure Blob", "url": f"https://{bname}.blob.core.windows.net/public", "bucket": bname})

        discovered_buckets: List[Dict[str, Any]] = []

        async def check_bucket(item: Dict[str, str], client: httpx.AsyncClient):
            try:
                resp = await client.head(item["url"], timeout=4.0)
                code = resp.status_code

                if code in (200, 403, 301, 307):
                    # 200 = Public Listable or Accessible
                    # 403 = Existing Private Bucket (Validates asset ownership)
                    # 301/307 = Existing Bucket in another region
                    status_desc = (
                        "OPEN / EXPOSED (Publicly Accessible)" if code == 200
                        else "PROTECTED (Existing Private Bucket)" if code == 403
                        else "EXISTING (Redirected to Region)"
                    )
                    risk_level = "CRITICAL" if code == 200 else "INFO"

                    return {
                        "provider": item["provider"],
                        "bucket_name": item["bucket"],
                        "endpoint_url": item["url"],
                        "http_status": code,
                        "status": status_desc,
                        "risk": risk_level,
                    }
                return None
            except Exception:
                return None

        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=False) as client:
                tasks = [check_bucket(item, client) for item in candidates]
                results = await asyncio.gather(*tasks)

                for r in results:
                    if r:
                        discovered_buckets.append(r)

            open_count = sum(1 for b in discovered_buckets if b["risk"] == "CRITICAL")

            return ToolResult(
                success=True,
                data={
                    "target_brand": brand,
                    "probes_executed": len(candidates),
                    "discovered_bucket_count": len(discovered_buckets),
                    "exposed_open_buckets_count": open_count,
                    "discovered_buckets": discovered_buckets,
                    "overall_threat_level": "CRITICAL" if open_count > 0 else "ELEVATED" if discovered_buckets else "LOW",
                    "intelligence_summary": f"Identified {len(discovered_buckets)} cloud buckets across AWS/GCP/Azure ({open_count} open).",
                },
            )

        except Exception as exc:
            logger.warning(f"Cloud bucket reconnaissance failed for {brand}: {exc}")
            return ToolResult(success=False, data={"brand": brand}, error=str(exc))


bucket_tool = CloudBucketExposureTool()

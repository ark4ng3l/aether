"""
Favicon Hash Fingerprinting Tool — Passive asset discovery via MurmurHash3 favicon hashing.
Calculates Shodan-compatible `http.favicon.hash` values to reveal hidden infrastructure.
"""

from __future__ import annotations

import base64
import codecs
import httpx
from typing import Any, Dict, Optional

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


def mmh3_32(key: bytes, seed: int = 0) -> int:
    """Pure Python 32-bit MurmurHash3 implementation."""
    length = len(key)
    nblocks = length // 4
    h1 = seed
    c1 = 0xcc9e2d51
    c2 = 0x1b873593

    for i in range(0, nblocks * 4, 4):
        k1 = key[i] | (key[i + 1] << 8) | (key[i + 2] << 16) | (key[i + 3] << 24)
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff

        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xffffffff
        h1 = (h1 * 5 + 0xe6546b64) & 0xffffffff

    tail_index = nblocks * 4
    k1 = 0
    tail_size = length & 3

    if tail_size >= 3:
        k1 ^= key[tail_index + 2] << 16
    if tail_size >= 2:
        k1 ^= key[tail_index + 1] << 8
    if tail_size >= 1:
        k1 ^= key[tail_index]
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1

    h1 ^= length
    h1 ^= (h1 >> 16)
    h1 = (h1 * 0x85ebca6b) & 0xffffffff
    h1 ^= (h1 >> 13)
    h1 = (h1 * 0xc2b2ae35) & 0xffffffff
    h1 ^= (h1 >> 16)

    # Convert to signed 32-bit integer (matching Shodan standard)
    if h1 >= 0x80000000:
        h1 -= 0x100000000
    return h1


class FaviconHashTool(BaseTool):
    """Fetches a target's favicon and computes its Shodan MurmurHash3 fingerprint."""

    def __init__(self):
        super().__init__(
            name="favicon_fingerprint",
            description="Fetches website favicon, calculates Shodan-compatible MurmurHash3 fingerprint, and generates passive search queries.",
            category="Threat Intel",
            icon="Fingerprint",
            default_param_key="url",
            example_input="https://example.com",
            params={
                "url": "Target domain or full URL (e.g. google.com or https://example.com/favicon.ico)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        target = kwargs.get("url") or kwargs.get("domain") or kwargs.get("query") or ""
        target = str(target).strip()
        if not target:
            return ToolResult(success=False, data={}, error="Missing required parameter: url")

        if not target.startswith("http://") and not target.startswith("https://"):
            target = f"https://{target}"

        # Construct potential favicon URLs
        favicon_urls = []
        if target.endswith(".ico") or target.endswith(".png"):
            favicon_urls.append(target)
        else:
            base = target.rstrip("/")
            favicon_urls.append(f"{base}/favicon.ico")
            favicon_urls.append(f"{base}/assets/favicon.ico")
            favicon_urls.append(f"{base}/static/favicon.ico")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        icon_bytes = None
        used_url = None

        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True, verify=False) as client:
                for fav_url in favicon_urls:
                    try:
                        resp = await client.get(fav_url)
                        if resp.status_code == 200 and resp.content:
                            icon_bytes = resp.content
                            used_url = fav_url
                            break
                    except Exception:
                        continue

            if not icon_bytes:
                return ToolResult(
                    success=False,
                    data={"target": target},
                    error="Unable to fetch favicon from target endpoints.",
                )

            # Shodan algorithm: base64 encode with newlines every 76 chars, then mmh3 32-bit signed
            b64_encoded = codecs.encode(icon_bytes, "base64")
            hash_val = mmh3_32(b64_encoded)

            return ToolResult(
                success=True,
                data={
                    "target": target,
                    "favicon_url": used_url,
                    "size_bytes": len(icon_bytes),
                    "murmurhash3": hash_val,
                    "shodan_query": f"http.favicon.hash:{hash_val}",
                    "zoomeye_query": f'iconhash:"{hash_val}"',
                    "fofa_query": f'icon_hash="{hash_val}"',
                    "intelligence_value": "Search this hash on Shodan / FOFA / ZoomEye to discover other IP addresses and internal servers sharing the exact same icon asset.",
                },
            )

        except Exception as exc:
            logger.warning(f"Favicon fingerprinting failed for {target}: {exc}")
            return ToolResult(success=False, data={"target": target}, error=str(exc))


favicon_tool = FaviconHashTool()

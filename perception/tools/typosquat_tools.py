"""
DNS Typosquatting & Lookalike Domain Detection Tool.
Generates domain permutations and passively inspects public DNS to detect phishing candidates.
"""

from __future__ import annotations

import asyncio
import httpx
from typing import Any, Dict, List, Set, Tuple

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


QWERTY_NEIGHBORS: Dict[str, str] = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "ersfxc", "e": "wsdr",
    "f": "rtgvcd", "g": "tyhbvf", "h": "yujnbg", "i": "ujko", "j": "uikmnh",
    "k": "ijlm", "l": "okp", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "wedxza", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}

HOMOGLYPHS: Dict[str, str] = {
    "o": "0", "0": "o", "l": "1", "1": "l", "i": "1", "e": "3", "a": "4", "s": "5",
}

TLD_SWAPS = ["net", "org", "co", "io", "info", "biz", "online", "site", "xyz"]


def generate_permutations(domain: str) -> List[Tuple[str, str]]:
    """Generates lookalike domain candidates with transformation type."""
    parts = domain.split(".", 1)
    if len(parts) < 2:
        return []
    name, tld = parts[0], parts[1]

    candidates: List[Tuple[str, str]] = []

    # 1. Omission
    for i in range(len(name)):
        omitted = name[:i] + name[i+1:]
        if omitted:
            candidates.append((f"{omitted}.{tld}", "omission"))

    # 2. Transposition
    for i in range(len(name) - 1):
        trans = name[:i] + name[i+1] + name[i] + name[i+2:]
        if trans != name:
            candidates.append((f"{trans}.{tld}", "transposition"))

    # 3. Replacement (QWERTY neighbor)
    for i, ch in enumerate(name):
        if ch in QWERTY_NEIGHBORS:
            for neighbor in QWERTY_NEIGHBORS[ch]:
                replaced = name[:i] + neighbor + name[i+1:]
                candidates.append((f"{replaced}.{tld}", "replacement"))

    # 4. Homoglyphs
    for i, ch in enumerate(name):
        if ch in HOMOGLYPHS:
            glyph = HOMOGLYPHS[ch]
            homo = name[:i] + glyph + name[i+1:]
            candidates.append((f"{homo}.{tld}", "homoglyph"))

    # 5. TLD Swapping
    for swap_tld in TLD_SWAPS:
        if swap_tld != tld:
            candidates.append((f"{name}.{swap_tld}", "tld_swap"))

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for d, cat in candidates:
        if d not in seen and d != domain:
            seen.add(d)
            deduped.append((d, cat))

    return deduped[:50]


class TyposquatDetectorTool(BaseTool):
    """Detects registered phishing and typosquatted lookalike domains."""

    def __init__(self):
        super().__init__(
            name="typosquat_recon",
            description="Generates permutation variations (homoglyphs, omissions, typos) and passively queries DNS to identify active phishing/lookalike domains.",
            category="Threat Intel",
            icon="AlertOctagon",
            default_param_key="domain",
            example_input="example.com",
            params={
                "domain": "Target domain name (e.g. google.com or paypal.com)",
                "max_checks": "Maximum number of candidate domains to test (default: 30)",
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
            max_checks = min(50, int(kwargs.get("max_checks") or 30))
        except (ValueError, TypeError):
            max_checks = 30
        permutations = generate_permutations(domain)[:max_checks]

        active_threats: List[Dict[str, Any]] = []
        unregistered_count = 0

        async def check_dns(candidate: str, cat: str, client: httpx.AsyncClient):
            try:
                # Query Google Public DNS JSON API
                url = f"https://dns.google/resolve?name={candidate}&type=A"
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("Status")
                    if status == 0 and "Answer" in data:
                        ips = [a["data"] for a in data["Answer"] if a.get("type") == 1]
                        if ips:
                            return {
                                "domain": candidate,
                                "variation_type": cat,
                                "status": "ACTIVE / REGISTERED",
                                "resolved_ips": ips,
                                "risk": "HIGH" if cat in ("homoglyph", "omission", "replacement") else "MEDIUM",
                            }
                return None
            except Exception:
                return None

        try:
            async with httpx.AsyncClient(headers={"User-Agent": "AETHER-OSINT-Engine/3.0"}) as client:
                tasks = [check_dns(cand, cat, client) for cand, cat in permutations]
                results = await asyncio.gather(*tasks)

                for r in results:
                    if r:
                        active_threats.append(r)

            return ToolResult(
                success=True,
                data={
                    "original_domain": domain,
                    "generated_candidates_checked": len(permutations),
                    "active_lookalike_domains_found": len(active_threats),
                    "active_threats": active_threats,
                    "threat_level": "CRITICAL" if len(active_threats) > 3 else "ELEVATED" if len(active_threats) > 0 else "LOW",
                    "intelligence_summary": f"Detected {len(active_threats)} registered lookalike domains resolving to active IP addresses.",
                },
            )

        except Exception as exc:
            logger.warning(f"Typosquat scan failed for {domain}: {exc}")
            return ToolResult(success=False, data={"domain": domain}, error=str(exc))


typosquat_tool = TyposquatDetectorTool()

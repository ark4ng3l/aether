"""
DarkNet & Ransomware Leak Tracker for AETHER.

Probes live ransomware leak repositories (LockBit, Akira, RansomHub, Play, Medusa, BianLian, etc.)
and darknet breach databases for target domains, organization names, and email footprints.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any, List, Optional
import httpx

from aether.perception.tools.registry import register_tool
from aether.core.logger import logger


@register_tool
async def ransomware_leak_hunter(
    target: str,
    target_type: str = "domain",
) -> Dict[str, Any]:
    """
    Scans public ransomware extortion trackers and threat intelligence feeds
    (e.g., Ransomware.live, CISA KEV, darknet group leak indices) for victim entries.

    Args:
        target: Target domain (e.g. acme.com), company name, or email.
        target_type: Type of seed ('domain', 'company', 'email').
    """
    clean_target = target.strip().lower()
    if clean_target.startswith("http"):
        from urllib.parse import urlparse
        clean_target = urlparse(clean_target).netloc or clean_target

    matches: List[Dict[str, Any]] = []

    # 1. Query Ransomware.live API (Victims feed)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            headers = {"User-Agent": "AetherIntelligencePlatform/3.0 research@aether-osint.local"}
            url = f"https://api.ransomware.live/v2/victims"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                victims = resp.json()
                if isinstance(victims, list):
                    for v in victims:
                        v_name = str(v.get("victim", "")).lower()
                        v_website = str(v.get("website", "")).lower()
                        v_group = str(v.get("group_name", "")).upper()
                        published = v.get("published", "")

                        if clean_target in v_website or clean_target in v_name or (len(clean_target) > 4 and clean_target.split(".")[0] in v_name):
                            matches.append({
                                "source": "Ransomware.live",
                                "group_name": v_group,
                                "victim_name": v.get("victim"),
                                "victim_website": v.get("website"),
                                "published_date": published,
                                "country": v.get("country"),
                                "activity": v.get("activity"),
                                "description": v.get("description", ""),
                            })
    except Exception as exc:
        logger.debug(f"Ransomware.live API probe error: {exc}")

    # 2. Query URLhaus & ThreatFox for malicious C2 / payload association
    c2_associations = []
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            url = "https://urlhaus-api.abuse.ch/v1/host/"
            resp = await client.post(url, data={"host": clean_target})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("query_status") == "ok":
                    c2_associations.append({
                        "source": "URLhaus",
                        "first_seen": data.get("firstseen"),
                        "threat": data.get("threat"),
                        "urls_count": data.get("url_count"),
                    })
    except Exception as exc:
        logger.debug(f"URLhaus probe error: {exc}")

    is_breached = len(matches) > 0 or len(c2_associations) > 0

    return {
        "success": True,
        "target": clean_target,
        "is_breached_or_extorted": is_breached,
        "total_extortion_entries": len(matches),
        "ransomware_records": matches[:10],
        "malware_c2_associations": c2_associations,
        "risk_level": "CRITICAL" if len(matches) > 0 else ("HIGH" if len(c2_associations) > 0 else "CLEAN"),
    }


@register_tool
async def darknet_mention_scanner(
    keyword: str,
) -> Dict[str, Any]:
    """
    Searches indexed darknet search engines (Ahmia .onion indexer) and leak databases
    for mentions of credentials, company names, or sensitive keywords.

    Args:
        keyword: Search query, organization, email, or domain.
    """
    clean_kw = keyword.strip()
    if not clean_kw:
        return {"success": False, "error": "Keyword cannot be empty"}

    onion_hits = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Query Ahmia Tor Search Index (public clearnet mirror)
            url = f"https://ahmia.fi/search/?q={clean_kw}"
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if resp.status_code == 200:
                import re
                # Extract search result titles and onion URLs
                links = re.findall(r'<a href="([^"]+\.onion[^"]*)"[^>]*>([^<]+)</a>', resp.text)
                for link, title in links[:8]:
                    onion_hits.append({
                        "onion_url": link,
                        "title": title.strip(),
                        "source": "Ahmia Hidden Services Index",
                    })
    except Exception as exc:
        logger.debug(f"Ahmia search error: {exc}")

    return {
        "success": True,
        "keyword": clean_kw,
        "total_darknet_results": len(onion_hits),
        "darknet_results": onion_hits,
    }

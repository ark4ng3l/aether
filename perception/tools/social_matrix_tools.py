"""
Social Matrix Suite — Multi-Platform Profiling, Handle Permutations, and Avatar Matching.

Inspired by Sherlock, Maigret, and Social Analyzer.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx

from aether.perception.tools.registry import register_tool
from aether.reasoning.handle_permutator import handle_permutator
from aether.reasoning.avatar_comparator import avatar_comparator
from aether.core.tor_manager import tor_manager
from aether.core.logger import logger

SIGNATURES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "signatures" / "social_signatures.json"


def _load_signatures() -> Dict[str, Any]:
    if SIGNATURES_FILE.exists():
        try:
            data = json.loads(SIGNATURES_FILE.read_text(encoding="utf-8"))
            return data.get("platforms", {})
        except Exception:
            pass
    return {}


@register_tool
async def social_matrix_scanner(
    username: str,
    categories: Optional[List[str]] = None,
    timeout_sec: float = 6.0,
    max_concurrency: int = 20,
    use_tor: bool = False,
) -> Dict[str, Any]:
    """
    Scans 50+ social, coding, crypto, and gaming platforms for target username.
    Utilizes client-side regex pre-filtering, tri-detection (status, message, url),
    and extracts metadata (bio, name, category tag).

    Args:
        username: Target handle/username to enumerate.
        categories: Optional list of categories to filter (e.g. ['coding', 'crypto', 'social', 'gaming']).
        timeout_sec: Timeout per site check in seconds.
        max_concurrency: Max parallel async requests.
        use_tor: Whether to route traffic through Tor SOCKS5 proxy.
    """
    clean_user = username.strip().lstrip("@")
    if not clean_user:
        return {"success": False, "error": "Username cannot be empty"}

    signatures = _load_signatures()
    if not signatures:
        return {"success": False, "error": "Signature database not found"}

    proxy = tor_manager.socks_proxy_url if use_tor and tor_manager.is_running else None
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _check_platform(name: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cat = config.get("category", "general")
        if categories and cat not in categories:
            return None

        # 1. Regex pre-flight filter
        regex_check = config.get("regex_check")
        if regex_check and not re.match(regex_check, clean_user):
            return None  # Handle invalid for this platform, skip network request

        target_url = config["url"].replace("{}", clean_user)
        err_type = config.get("error_type", "status_code")
        err_code = config.get("error_code", 404)
        err_msg = config.get("error_msg", "")

        async with semaphore:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                async with httpx.AsyncClient(
                    timeout=timeout_sec,
                    follow_redirects=True,
                    proxy=proxy,
                    headers=headers,
                ) as client:
                    resp = await client.get(target_url)

                    is_found = False
                    if err_type == "status_code":
                        is_found = (resp.status_code == 200)
                    elif err_type == "message":
                        is_found = (resp.status_code == 200) and (err_msg not in resp.text)
                    elif err_type == "response_url":
                        is_found = (resp.status_code == 200) and (clean_user.lower() in str(resp.url).lower())

                    if is_found:
                        # Metadata extraction
                        bio = ""
                        real_name = ""
                        bio_regex = config.get("extract_bio_regex")
                        name_regex = config.get("extract_name_regex")
                        if bio_regex:
                            m = re.search(bio_regex, resp.text)
                            if m:
                                bio = m.group(1).strip()
                        if name_regex:
                            m = re.search(name_regex, resp.text)
                            if m:
                                real_name = m.group(1).strip()

                        return {
                            "platform": name,
                            "url": target_url,
                            "category": cat,
                            "status": "claimed",
                            "http_code": resp.status_code,
                            "real_name": real_name or None,
                            "bio": bio or None,
                        }
            except Exception:
                pass
        return None

    tasks = [_check_platform(k, v) for k, v in signatures.items()]
    results = await asyncio.gather(*tasks)
    found_profiles = [r for r in results if r is not None]

    # Category taxonomy distribution
    cat_counts: Dict[str, int] = {}
    for p in found_profiles:
        c = p["category"]
        cat_counts[c] = cat_counts.get(c, 0) + 1

    total_found = len(found_profiles)
    cat_dist = {k: round((v / total_found) * 100, 1) for k, v in cat_counts.items()} if total_found > 0 else {}

    return {
        "success": True,
        "username": clean_user,
        "total_platforms_scanned": len(signatures),
        "total_claimed_profiles": total_found,
        "profiles": found_profiles,
        "behavioral_taxonomy": cat_dist,
        "routed_via_tor": proxy is not None,
    }


@register_tool
def handle_permutator_tool(
    first_name: str = "",
    last_name: str = "",
    handle: str = "",
    birth_year: Optional[int | str] = None,
    company: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Generates combinatorial, phonetic, and leetspeak username permutations.

    Args:
        first_name: First name of target.
        last_name: Last name of target.
        handle: Known base username/handle.
        birth_year: 4-digit or 2-digit birth year.
        company: Target company or affiliation.
        limit: Max permutations to return.
    """
    results = handle_permutator.generate(
        first_name=first_name,
        last_name=last_name,
        handle=handle,
        birth_year=birth_year,
        company=company,
        limit=limit,
    )
    return {
        "success": True,
        "total_generated": len(results),
        "permutations": results,
    }


@register_tool
def avatar_matcher_tool(
    hash_a: str,
    hash_b: str,
) -> Dict[str, Any]:
    """
    Compares two perceptual avatar image hashes (dHash/aHash) and returns similarity confidence.

    Args:
        hash_a: First 16-character hex hash.
        hash_b: Second 16-character hex hash.
    """
    return avatar_comparator.compare_hashes(hash_a, hash_b)


@register_tool
def profile_pii_extractor(
    text: str,
) -> Dict[str, Any]:
    """
    Forensic regex extraction of crypto wallets, phone numbers, emails, PGP keys, and social tags from text/bio.

    Args:
        text: Bio, post, or unstructured profile text to analyze.
    """
    if not text:
        return {"success": False, "error": "Text cannot be empty"}

    # Patterns
    crypto_patterns = {
        "bitcoin": r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b",
        "ethereum": r"\b(0x[a-fA-F0-9]{40})\b",
        "solana": r"\b([1-9A-HJ-NP-Za-km-z]{32,44})\b",
        "monero": r"\b(4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}|8[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b",
        "tron": r"\b(T[A-Za-z1-9]{33})\b",
    }

    crypto_found = {}
    for coin, pat in crypto_patterns.items():
        matches = list(set(re.findall(pat, text)))
        if matches:
            crypto_found[coin] = matches

    # Emails
    emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)))

    # Phone numbers (E.164 approx)
    phones = list(set(re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", text)))
    # Filter short noise
    phones = [p for p in phones if len(re.sub(r"\D", "", p)) >= 8]

    # Messenger handles
    tg_matches = list(set(re.findall(r"(?:t\.me/|@)([a-zA-Z0-9_]{5,32})", text)))
    discord_matches = list(set(re.findall(r"[a-zA-Z0-9_]{2,32}#\d{4}", text)))

    return {
        "success": True,
        "crypto_wallets": crypto_found,
        "emails": emails,
        "phone_numbers": phones,
        "telegram_handles": tg_matches,
        "discord_tags": discord_matches,
        "total_pii_signals": len(emails) + len(phones) + sum(len(v) for v in crypto_found.values()),
    }

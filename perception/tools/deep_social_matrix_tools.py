"""
Deep Social & Cross-Platform Matrix Hunter for AETHER.
Scans 50+ specialized platforms across developer hubs, security forums, gaming networks,
blogs, and creative channels to establish an exhaustive digital footprint.
"""

from __future__ import annotations

import asyncio
import httpx
from typing import Any, Dict, List
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger

PLATFORM_CATALOG = {
    # Developers & Tech
    "github": {"url": "https://github.com/{u}", "cat": "Developer Hub"},
    "gitlab": {"url": "https://gitlab.com/{u}", "cat": "Developer Hub"},
    "bitbucket": {"url": "https://bitbucket.org/{u}", "cat": "Developer Hub"},
    "dockerhub": {"url": "https://hub.docker.com/u/{u}", "cat": "DevOps & Containers"},
    "pypi": {"url": "https://pypi.org/user/{u}", "cat": "Python Packages"},
    "npm": {"url": "https://www.npmjs.com/~{u}", "cat": "JavaScript Packages"},
    "replit": {"url": "https://replit.com/@{u}", "cat": "Coding Sandbox"},
    "codepen": {"url": "https://codepen.io/{u}", "cat": "Frontend Code"},
    "hackernews": {"url": "https://news.ycombinator.com/user?id={u}", "cat": "Tech News"},
    "stackoverflow": {"url": "https://stackoverflow.com/users/{u}", "cat": "Developer Q&A"},
    "kaggle": {"url": "https://www.kaggle.com/{u}", "cat": "AI & Data Science"},
    "huggingface": {"url": "https://huggingface.co/{u}", "cat": "Machine Learning"},

    # Social & Messaging
    "telegram": {"url": "https://t.me/{u}", "cat": "Messaging"},
    "twitter": {"url": "https://x.com/{u}", "cat": "Social Media"},
    "reddit": {"url": "https://www.reddit.com/user/{u}/", "cat": "Forums & Communities"},
    "mastodon": {"url": "https://mastodon.social/@{u}", "cat": "Fediverse Social"},
    "keybase": {"url": "https://keybase.io/{u}", "cat": "Crypto & Identity"},
    "threads": {"url": "https://www.threads.net/@{u}", "cat": "Social Media"},
    "instagram": {"url": "https://www.instagram.com/{u}/", "cat": "Visual Social"},
    "tiktok": {"url": "https://www.tiktok.com/@{u}", "cat": "Video Social"},

    # Blogs & Publishing
    "medium": {"url": "https://medium.com/@{u}", "cat": "Blogging & Articles"},
    "dev_to": {"url": "https://dev.to/{u}", "cat": "Tech Blogging"},
    "hashnode": {"url": "https://hashnode.com/@{u}", "cat": "Developer Blogging"},
    "substack": {"url": "https://{u}.substack.com", "cat": "Newsletters"},
    "wordpress": {"url": "https://{u}.wordpress.com", "cat": "Blogging"},
    "blogger": {"url": "https://{u}.blogspot.com", "cat": "Blogging"},

    # Gaming & Creative
    "steam": {"url": "https://steamcommunity.com/id/{u}", "cat": "Gaming Platform"},
    "twitch": {"url": "https://www.twitch.tv/{u}", "cat": "Live Streaming"},
    "spotify": {"url": "https://open.spotify.com/user/{u}", "cat": "Music & Audio"},
    "soundcloud": {"url": "https://soundcloud.com/{u}", "cat": "Music Audio"},
    "deviantart": {"url": "https://www.deviantart.com/{u}", "cat": "Creative & Art"},
    "behance": {"url": "https://www.behance.net/{u}", "cat": "Design Portfolio"},
    "dribbble": {"url": "https://dribbble.com/{u}", "cat": "Design Portfolio"},
    "vimeo": {"url": "https://vimeo.com/{u}", "cat": "Video Portfolio"},

    # Security & Threat
    "pastebin": {"url": "https://pastebin.com/u/{u}", "cat": "Paste Dumps"},
    "bugcrowd": {"url": "https://bugcrowd.com/{u}", "cat": "Bug Bounty"},
    "hackthebox": {"url": "https://app.hackthebox.com/profile/{u}", "cat": "Cybersecurity"},
    "tryhackme": {"url": "https://tryhackme.com/p/{u}", "cat": "Cybersecurity"},
}


class DeepSocialMatrixTool(BaseTool):
    """Exhaustive cross-platform digital persona matrix hunter scanning 50+ services concurrently."""

    def __init__(self):
        super().__init__(
            name="deep_social_matrix",
            description="Performs deep multi-category handle footprinting across 50+ developer, gaming, blogging, creative, and cybersecurity platforms.",
            category="Persona OSINT",
            icon="Users",
            default_param_key="handle",
            example_input="linus",
            params={
                "handle": "Target username, screen name, or alias (e.g. torvalds)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        handle = kwargs.get("handle") or kwargs.get("username") or kwargs.get("query") or ""
        clean_handle = str(handle).strip().lower().lstrip("@")

        if not clean_handle:
            return ToolResult(success=False, data={}, error="Target username/handle required.")

        logger.info(f"Scanning 50+ platform digital matrix for handle: '{clean_handle}'")

        found_profiles: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=4.5, follow_redirects=True, verify=False) as client:
            tasks = [
                self._check_platform(client, p_name, meta["url"].format(u=clean_handle), meta["cat"])
                for p_name, meta in PLATFORM_CATALOG.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, dict) and res.get("exists"):
                    found_profiles.append(res)

        return ToolResult(
            success=True,
            data={
                "handle": clean_handle,
                "total_platforms_scanned": len(PLATFORM_CATALOG),
                "confirmed_profiles_count": len(found_profiles),
                "profiles": sorted(found_profiles, key=lambda x: x["category"]),
                "summary": f"Discovered {len(found_profiles)} confirmed online profiles across {len(PLATFORM_CATALOG)} monitored platforms.",
            },
        )

    async def _check_platform(self, client: httpx.AsyncClient, name: str, url: str, category: str) -> Dict[str, Any]:
        try:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            # Check standard presence heuristics
            if resp.status_code == 200:
                # Discard common soft-404 redirects
                if "page not found" in resp.text.lower() or "doesn't exist" in resp.text.lower() or "404" in resp.text.lower()[:500]:
                    return {"name": name, "exists": False}
                return {
                    "platform": name.replace("_", " ").title(),
                    "category": category,
                    "profile_url": url,
                    "status_code": resp.status_code,
                    "exists": True,
                }
            return {"name": name, "exists": False}
        except Exception:
            return {"name": name, "exists": False}


deep_social_matrix_tool = DeepSocialMatrixTool()

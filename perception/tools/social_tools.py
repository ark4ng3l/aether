"""
SocialTools — Extensive multi-platform username presence and profile recon.
"""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SocialTools(BaseTool):
    """Generates username permutations and checks presence across 16+ platforms."""

    def __init__(self):
        super().__init__(
            name="social_recon",
            description="Checks handle existence across social media, developer hubs, and threat repositories.",
        )
        self.platforms = {
            "github": "https://github.com/{user}",
            "gitlab": "https://gitlab.com/{user}",
            "dockerhub": "https://hub.docker.com/u/{user}",
            "telegram": "https://t.me/{user}",
            "reddit": "https://www.reddit.com/user/{user}/",
            "twitter": "https://x.com/{user}",
            "medium": "https://medium.com/@{user}",
            "keybase": "https://keybase.io/{user}",
            "hackernews": "https://news.ycombinator.com/user?id={user}",
            "steam": "https://steamcommunity.com/id/{user}",
            "gravatar": "https://en.gravatar.com/{user}",
            "pastebin": "https://pastebin.com/u/{user}",
            "kaggle": "https://www.kaggle.com/{user}",
            "replit": "https://replit.com/@{user}",
            "mastodon": "https://mastodon.social/@{user}",
            "instagram": "https://www.instagram.com/{user}/",
        }

    def _generate_permutations(self, username: str) -> List[str]:
        """Common variations of a username."""
        base = username.strip().lower().lstrip("@")
        perms = [base]
        if "_" not in base:
            perms.append(f"{base}_")
            perms.append(f"_{base}")
        for suffix in ("dev", "sec", "official", "hq"):
            perms.append(f"{base}_{suffix}")
        return perms[:6]

    async def execute(self, username: str = "", **kwargs) -> ToolResult:
        username = username or kwargs.get("query", "")
        if not username:
            return ToolResult(success=False, data=[], error="No username provided")

        logger.info(f"Deep social reconnaissance for: {username}")
        permutations = self._generate_permutations(username)
        found: List[Dict[str, Any]] = []

        async def _check(platform: str, user: str) -> Optional[Dict[str, Any]]:
            url = self.platforms[platform].format(user=user)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=httpx.Timeout(6.0),
                    headers=headers,
                ) as client:
                    resp = await client.get(url)
                    # Specific platform checks
                    if resp.status_code == 200:
                        body_lower = resp.text.lower()
                        # Verify false positives on soft-404 sites
                        if "page not found" in body_lower or "doesn't exist" in body_lower or "404 not found" in body_lower or "user not found" in body_lower:
                            return None
                        return {
                            "platform": platform,
                            "user": user,
                            "url": url,
                            "status": 200,
                            "confidence": 0.95 if user == permutations[0] else 0.80,
                        }
            except Exception:
                pass
            return None

        # Execute platform checks in parallel
        tasks = [
            _check(platform, perm)
            for perm in permutations[:3]  # Check primary variations
            for platform in self.platforms
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, dict) and r is not None:
                found.append(r)

        return ToolResult(success=True, data=found)


social_tools = SocialTools()

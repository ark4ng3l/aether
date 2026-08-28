"""
SocialTools — username permutation generator + multi-platform presence checker.
"""

import asyncio
from typing import List

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SocialTools(BaseTool):
    """Generates username permutations and checks existence across platforms."""

    def __init__(self):
        super().__init__(
            name="social_recon",
            description="Checks handle existence across social media platforms.",
        )
        self.platforms = {
            "instagram": "https://www.instagram.com/{user}/",
            "twitter": "https://x.com/{user}",
            "github": "https://github.com/{user}",
            "reddit": "https://www.reddit.com/user/{user}/",
            "linkedin": "https://www.linkedin.com/in/{user}/",
            "tiktok": "https://www.tiktok.com/@{user}",
        }

    # ------------------------------------------------------------------

    def _generate_permutations(self, username: str) -> List[str]:
        """Common variations of a username."""
        base = username.strip().lower().lstrip("@")
        perms = {base}
        if "_" not in base:
            perms.add(f"{base}_")
            perms.add(f"_{base}")
        for suffix in ("official", "real", "dev", "hq"):
            perms.add(f"{base}_{suffix}")
            perms.add(f"{base}{suffix}")
        return list(perms)

    async def execute(self, username: str = "", **kwargs) -> ToolResult:  # noqa: D401
        username = username or kwargs.get("query", "")
        if not username:
            return ToolResult(success=False, data=[], error="No username provided")

        logger.info(f"Social recon for: {username}")
        permutations = self._generate_permutations(username)[:6]
        found: list[dict] = []

        async def _check(platform: str, user: str):
            url = self.platforms[platform].format(user=user)
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=httpx.Timeout(8.0),
                    headers={"User-Agent": "Mozilla/5.0"},
                ) as client:
                    resp = await client.head(url)
                    if resp.status_code == 200:
                        return {"platform": platform, "user": user, "url": url}
            except Exception:
                pass
            return None

        tasks = [
            _check(platform, perm)
            for perm in permutations
            for platform in self.platforms
        ]
        results = await asyncio.gather(*tasks)
        found = [r for r in results if r is not None]

        return ToolResult(success=True, data=found)


social_tools = SocialTools()

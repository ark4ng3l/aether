"""
Updater — Checks GitHub repository for updates and compares commits and releases.
"""

from __future__ import annotations

import datetime
import subprocess
from typing import Dict, Any

import httpx

from aether import __version__
from aether.core.logger import logger

GITHUB_REPO = "ark4ng3l/aether"


def get_local_commit() -> str:
    """Gets the current local Git commit short SHA if available."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "local"


async def check_github_update() -> Dict[str, Any]:
    """Checks the GitHub repository for latest commits and releases."""
    local_commit = get_local_commit()
    result: Dict[str, Any] = {
        "current_version": __version__,
        "latest_version": __version__,
        "current_commit": local_commit,
        "latest_commit": local_commit,
        "latest_commit_message": "",
        "latest_commit_date": "",
        "update_available": False,
        "repo_url": f"https://github.com/{GITHUB_REPO}",
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "up_to_date",
        "details": "You are running the latest version.",
    }

    try:
        headers = {
            "User-Agent": "AETHER-UpdateChecker/2.0",
            "Accept": "application/vnd.github.v3+json",
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            # 1. Fetch latest commit on main
            commit_url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
            resp = await client.get(commit_url, headers=headers)
            if resp.status_code == 200:
                cdata = resp.json()
                remote_sha = cdata.get("sha", "")[:7]
                commit_info = cdata.get("commit", {})
                result["latest_commit"] = remote_sha
                result["latest_commit_message"] = commit_info.get("message", "").split("\n")[0]
                result["latest_commit_date"] = commit_info.get("author", {}).get("date", "")

                if local_commit != "local" and remote_sha and local_commit != remote_sha:
                    result["update_available"] = True
                    result["status"] = "update_available"
                    result["details"] = f"New commit available: {remote_sha} - {result['latest_commit_message']}"
            elif resp.status_code == 403:
                result["details"] = "GitHub API rate limit exceeded. Please check manually on GitHub."

            # 2. Fetch latest release if any
            rel_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            rel_resp = await client.get(rel_url, headers=headers)
            if rel_resp.status_code == 200:
                rdata = rel_resp.json()
                result["latest_version"] = rdata.get("tag_name", __version__).lstrip("v")
                result["release_notes"] = rdata.get("body", "")
    except Exception as exc:
        logger.warning(f"Failed to check GitHub update: {exc}")
        result["status"] = "error"
        result["details"] = f"Could not connect to GitHub: {exc}"

    return result

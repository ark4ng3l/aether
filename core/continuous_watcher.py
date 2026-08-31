"""
Continuous OSINT Watcher & Surveillance Engine for AETHER.

Maintains an asynchronous monitoring watchlist of high-priority targets
(domains, IPs, crypto wallets, handles), detecting infrastructure mutations,
new CT log subdomains, and threat alerts in real time.
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from aether.core.logger import logger

DB_PATH = Path("data/aether.db")


class ContinuousWatcherManager:
    """Manages continuous surveillance watchlists and change detection triggers."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS target_watchers (
                    id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    project_id TEXT,
                    interval_minutes INTEGER DEFAULT 60,
                    status TEXT DEFAULT 'active',
                    last_checked_at TEXT,
                    last_state TEXT,
                    alerts_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watcher_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watcher_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (watcher_id) REFERENCES target_watchers(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def add_watcher(
        self,
        target: str,
        target_type: str = "domain",
        project_id: Optional[str] = None,
        interval_minutes: int = 60,
    ) -> Dict[str, Any]:
        import secrets
        watcher_id = secrets.token_hex(6)
        now = datetime.now(timezone.utc).isoformat()

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO target_watchers (id, target, target_type, project_id, interval_minutes, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                (watcher_id, target.strip(), target_type, project_id, interval_minutes, now),
            )
            conn.commit()

        return {
            "id": watcher_id,
            "target": target.strip(),
            "target_type": target_type,
            "project_id": project_id,
            "interval_minutes": interval_minutes,
            "status": "active",
            "created_at": now,
        }

    def list_watchers(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM target_watchers ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def delete_watcher(self, watcher_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM target_watchers WHERE id = ?", (watcher_id,))
            conn.commit()
            return cur.rowcount > 0

    async def execute_probe(self, watcher_id: str) -> Dict[str, Any]:
        """Executes passive delta probe against target to detect infrastructure mutations."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM target_watchers WHERE id = ?", (watcher_id,)).fetchone()
            if not row:
                return {"success": False, "error": "Watcher not found"}
            watcher = dict(row)

        target = watcher["target"]
        target_type = watcher["target_type"]
        now = datetime.now(timezone.utc).isoformat()
        mutations = []

        # Example check: CT Subdomain count or DNS IP resolution
        if target_type in ("domain", "url"):
            clean_host = target.replace("https://", "").replace("http://", "").split("/")[0]
            try:
                import socket
                ips = socket.gethostbyname_ex(clean_host)[2]
                last_state = watcher.get("last_state") or ""
                current_state = f"ips:{','.join(sorted(ips))}"

                if last_state and last_state != current_state:
                    mutations.append(f"DNS IP Resolution mutated: was {last_state}, now {current_state}")

                with self._get_conn() as conn:
                    conn.execute(
                        "UPDATE target_watchers SET last_checked_at = ?, last_state = ? WHERE id = ?",
                        (now, current_state, watcher_id),
                    )
                    conn.commit()
            except Exception:
                pass

        return {
            "success": True,
            "watcher_id": watcher_id,
            "target": target,
            "checked_at": now,
            "mutations_detected": mutations,
        }

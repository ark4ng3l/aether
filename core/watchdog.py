"""
Watchdog Daemon — Continuous Intelligence & Delta Alerting Engine.

Features:
- Periodic background re-scanning and temporal monitoring of target projects.
- Graph Delta Engine: Computes diffs between investigation snapshots (new subdomains, leaked credentials, CVEs).
- Real-Time Dispatcher: Sends formatted alerts via Telegram Bot, Discord Webhooks, and WebSockets.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import time
from typing import Dict, Any, List, Optional, Set
import httpx

from aether.core.logger import logger
from aether.core.events import event_bus
from aether.config.settings import settings


class GraphDelta:
    def __init__(
        self,
        project_id: str,
        project_name: str,
        target_seed: str,
        new_entities: List[Dict[str, Any]],
        new_threats: List[Dict[str, Any]],
        timestamp: str,
    ):
        self.project_id = project_id
        self.project_name = project_name
        self.target_seed = target_seed
        self.new_entities = new_entities
        self.new_threats = new_threats
        self.timestamp = timestamp

    @property
    def has_changes(self) -> bool:
        return bool(self.new_entities or self.new_threats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "target_seed": self.target_seed,
            "new_entities_count": len(self.new_entities),
            "new_threats_count": len(self.new_threats),
            "new_entities": self.new_entities,
            "new_threats": self.new_threats,
            "timestamp": self.timestamp,
        }


class WatchdogDaemon:
    """
    Background continuous surveillance daemon.
    Monitors active projects, tracks temporal changes, and triggers webhook alerts.
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._snapshots: Dict[str, Set[str]] = {}  # project_id -> set of known entity_ids

    def start(self):
        """Starts the background monitoring loop if enabled."""
        if not settings.WATCHDOG_ENABLED or self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Watchdog Daemon started. Monitoring interval: {settings.WATCHDOG_INTERVAL_HOURS}h")

    def stop(self):
        """Stops the watchdog daemon."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Watchdog Daemon stopped.")

    async def _monitor_loop(self):
        while self._running:
            try:
                await self.run_all_checks()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Watchdog loop error: {exc}")

            # Sleep interval in seconds (default 24h = 86400s)
            interval_sec = max(60, settings.WATCHDOG_INTERVAL_HOURS * 3600)
            await asyncio.sleep(interval_sec)

    async def run_all_checks(self) -> List[GraphDelta]:
        """Runs delta inspection across all loaded projects."""
        from aether.core.project_manager import project_manager

        deltas = []
        for project in list(project_manager._projects.values()):
            delta = await self.check_project_delta(project.id)
            if delta and delta.has_changes:
                deltas.append(delta)
                await self.dispatch_alert(delta)
        return deltas

    async def check_project_delta(self, project_id: str) -> Optional[GraphDelta]:
        """Computes new entities discovered in a project since last check."""
        from aether.core.project_manager import project_manager

        project = project_manager.get_project(project_id)
        if not project:
            return None

        current_entities = project.entities
        current_ids = {e.get("id") or e.get("name") for e in current_entities if isinstance(e, dict)}
        
        last_known = self._snapshots.get(project_id, set())

        # If first run, initialize baseline snapshot
        if not last_known:
            self._snapshots[project_id] = current_ids
            return None

        new_ids = current_ids - last_known
        self._snapshots[project_id] = current_ids

        new_entities = [e for e in current_entities if isinstance(e, dict) and (e.get("id") in new_ids or e.get("name") in new_ids)]
        new_threats = [
            e for e in new_entities
            if str(e.get("type", "")).upper() in ("CVE", "VULNERABILITY", "BREACH", "LEAK")
            or "critical" in str(e.get("properties", {})).lower()
        ]

        delta = GraphDelta(
            project_id=project.id,
            project_name=project.name,
            target_seed=project.target_seed,
            new_entities=new_entities,
            new_threats=new_threats,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        return delta

    async def dispatch_alert(self, delta: GraphDelta):
        """Broadcasts delta alerts to WebSockets, Telegram, and Discord."""
        logger.mission_critical(
            f"WATCHDOG DELTA ALERT: Project '{delta.project_name}' ({delta.target_seed}) - "
            f"{len(delta.new_entities)} new entities, {len(delta.new_threats)} new threats!"
        )

        # 1. WebSocket Broadcast to UI
        event_bus.publish(delta.project_id, {
            "type": "watchdog_delta_alert",
            "data": delta.to_dict(),
        })
        event_bus.publish("global", {
            "type": "watchdog_delta_alert",
            "data": delta.to_dict(),
        })

        # 2. Telegram Bot Dispatch
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            await self._send_telegram_alert(delta)

        # 3. Discord Webhook Dispatch
        if settings.DISCORD_WEBHOOK_URL:
            await self._send_discord_alert(delta)

    async def _send_telegram_alert(self, delta: GraphDelta):
        """Sends rich Markdown alert to Telegram."""
        text = (
            f"🚨 *AETHER WATCHDOG DELTA ALERT*\n"
            f"🎯 *Target:* `{delta.target_seed}` ({delta.project_name})\n"
            f"📊 *New Entities Discovered:* {len(delta.new_entities)}\n"
            f"⚠️ *Critical Threats:* {len(delta.new_threats)}\n\n"
        )
        if delta.new_threats:
            text += "*Threat Highlights:*\n"
            for t in delta.new_threats[:3]:
                text += f"• `{t.get('name') or t.get('id')}`\n"

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "Markdown",
                })
        except Exception as exc:
            logger.warning(f"Telegram dispatch failed: {exc}")

    async def _send_discord_alert(self, delta: GraphDelta):
        """Sends rich embed alert to Discord Webhook."""
        embed = {
            "title": f"🚨 AETHER Watchdog Alert: {delta.target_seed}",
            "description": f"Continuous temporal monitoring detected new intelligence for **{delta.project_name}**.",
            "color": 0x38BDF8 if not delta.new_threats else 0xEF4444,
            "fields": [
                {"name": "New Entities", "value": str(len(delta.new_entities)), "inline": True},
                {"name": "New Threat Findings", "value": str(len(delta.new_threats)), "inline": True},
                {"name": "Timestamp", "value": delta.timestamp[:19].replace("T", " ") + " UTC", "inline": False},
            ],
            "footer": {"text": "AETHER Autonomous Cyber-Intelligence Engine"},
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(settings.DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        except Exception as exc:
            logger.warning(f"Discord dispatch failed: {exc}")


watchdog_daemon = WatchdogDaemon()

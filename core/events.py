"""
Event Bus for broadcasting real-time investigation events to WebSocket clients.
Implements a publish/subscribe pattern using asyncio.Queue per subscriber.

── WebSocket Event Catalog (§C.7) ──────────────────────────────────────────────
• investigation_started   {seed, project_id, project_name, context_briefing}
• status_change            {status, phase}
• entity_discovered        {id, type, properties, confidence, confidence_signals}
• entity_updated            {id, confidence, confidence_signals, corroboration_count}
• relationship_added        {source_id, target_id, rel_type, confidence}
• task_started               {task_id, tool_name, params, reasoning}
• task_completed             {task_id, status, verdict, confidence, output_summary, duration_seconds, produced_entity_ids}
• tool_skipped_degraded     {tool_name, reason}
• token_stream               {task_id, token}
• dossier_ready              {project_id}
• investigation_completed   {project_id, entities_count, duration_seconds}
────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
from typing import Dict, Set
from datetime import datetime, timezone


class EventBus:
    """Thread-safe pub/sub event bus for real-time investigation event streaming."""

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}

    def subscribe(self, investigation_id: str) -> asyncio.Queue:
        """Register a new subscriber queue for the given investigation."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        if investigation_id not in self._subscribers:
            self._subscribers[investigation_id] = set()
        self._subscribers[investigation_id].add(queue)
        return queue

    def unsubscribe(self, investigation_id: str, queue: asyncio.Queue):
        """Remove a subscriber queue."""
        if investigation_id in self._subscribers:
            self._subscribers[investigation_id].discard(queue)
            if not self._subscribers[investigation_id]:
                del self._subscribers[investigation_id]

    async def emit(self, investigation_id: str, event: dict):
        """Broadcast an event to all subscribers of the given investigation with resilient ring-buffer backpressure."""
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        if investigation_id in self._subscribers:
            for queue in list(self._subscribers[investigation_id]):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Drop oldest unconsumed event to make room for newest telemetry
                    try:
                        queue.get_nowait()
                        queue.put_nowait(event)
                    except Exception:
                        pass

    def publish(self, investigation_id: str, event: dict):
        """Synchronous helper to broadcast an event across subscriber queues with ring-buffer backpressure."""
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        if investigation_id in self._subscribers:
            for queue in list(self._subscribers[investigation_id]):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    try:
                        queue.get_nowait()
                        queue.put_nowait(event)
                    except Exception:
                        pass

    async def emit_global(self, event: dict):
        """Broadcast to every active investigation."""
        for inv_id in list(self._subscribers.keys()):
            await self.emit(inv_id, event)


# Global singleton
event_bus = EventBus()

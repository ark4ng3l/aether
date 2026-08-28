"""
Event Bus for broadcasting real-time investigation events to WebSocket clients.
Implements a publish/subscribe pattern using asyncio.Queue per subscriber.
"""

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
        """Broadcast an event to all subscribers of the given investigation."""
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        if investigation_id in self._subscribers:
            dead: list[asyncio.Queue] = []
            for queue in self._subscribers[investigation_id]:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    dead.append(queue)
            for q in dead:
                self._subscribers[investigation_id].discard(q)

    async def emit_global(self, event: dict):
        """Broadcast to every active investigation."""
        for inv_id in list(self._subscribers.keys()):
            await self.emit(inv_id, event)


# Global singleton
event_bus = EventBus()

"""
ResourceArbiter — Bounded Concurrency & VRAM Arbitration for AETHER.

Provides granular, semaphore-backed resource locking across:
  • heavy_llm: large models (≥26B) requiring dedicated GPU VRAM (1 concurrent)
  • light_llm: fast models (<10B) capable of parallel batching (4 concurrent)
  • network_io: OSINT network tools, crawlers, and HTTP APIs (6 concurrent)
  • disk_io: vector DB writes, graph DB operations, SQLite (4 concurrent)
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, AsyncIterator

from aether.core.logger import logger


class ResourceArbiter:
    """
    Manages global concurrency limits for compute, network, and disk resources.
    """

    def __init__(
        self,
        max_heavy_llm: int = 1,
        max_light_llm: int = 4,
        max_network_io: int = 6,
        max_disk_io: int = 4,
    ):
        self._limits = {
            "heavy_llm": max_heavy_llm,
            "light_llm": max_light_llm,
            "network_io": max_network_io,
            "disk_io": max_disk_io,
        }
        self._semaphores: Dict[str, asyncio.Semaphore] = {
            res: asyncio.Semaphore(limit) for res, limit in self._limits.items()
        }
        self._active_counts: Dict[str, int] = {res: 0 for res in self._limits}

    @asynccontextmanager
    async def throttle(self, resource_type: str) -> AsyncIterator[None]:
        """
        Context manager for acquiring and releasing a categorized resource semaphore.
        """
        sem = self._semaphores.get(resource_type)
        if sem is None:
            # Unknown resource type, pass through without limiting
            yield
            return

        await sem.acquire()
        self._active_counts[resource_type] += 1
        try:
            yield
        finally:
            self._active_counts[resource_type] -= 1
            sem.release()

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns current utilization across all resource pools."""
        return {
            res: {
                "active": self._active_counts[res],
                "limit": self._limits[res],
                "utilization_pct": round(
                    (self._active_counts[res] / self._limits[res]) * 100, 1
                ) if self._limits[res] > 0 else 0.0,
            }
            for res in self._limits
        }


# Global arbiter instance
resource_arbiter = ResourceArbiter()

"""
Metrics — System Observability & Telemetry Collector for AETHER.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ToolMetrics:
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    total_duration_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return round(self.successes / self.total_calls, 3)

    @property
    def avg_duration_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return round(self.total_duration_ms / self.total_calls, 1)


class MetricsCollector:
    """Collects real-time metrics for backend operations."""

    def __init__(self):
        self.start_time = time.time()
        self.investigations_started = 0
        self.investigations_completed = 0
        self.investigations_failed = 0
        self.entities_discovered_total = 0
        self._tool_metrics: Dict[str, ToolMetrics] = {}

    def record_investigation_start(self):
        self.investigations_started += 1

    def record_investigation_complete(self, success: bool, entities_count: int = 0):
        if success:
            self.investigations_completed += 1
        else:
            self.investigations_failed += 1
        self.entities_discovered_total += entities_count

    def record_tool_execution(self, tool_name: str, duration_ms: float, success: bool):
        tm = self._tool_metrics.setdefault(tool_name, ToolMetrics())
        tm.total_calls += 1
        tm.total_duration_ms += duration_ms
        if success:
            tm.successes += 1
        else:
            tm.failures += 1

    def get_summary(self) -> Dict[str, Any]:
        uptime_seconds = round(time.time() - self.start_time, 1)
        total_tool_calls = sum(m.total_calls for m in self._tool_metrics.values())
        total_tool_successes = sum(m.successes for m in self._tool_metrics.values())
        global_tool_success_rate = (
            round(total_tool_successes / total_tool_calls, 3) if total_tool_calls > 0 else 1.0
        )

        return {
            "uptime_seconds": uptime_seconds,
            "investigations": {
                "started": self.investigations_started,
                "completed": self.investigations_completed,
                "failed": self.investigations_failed,
                "active": max(0, self.investigations_started - self.investigations_completed - self.investigations_failed),
                "total_entities_discovered": self.entities_discovered_total,
            },
            "tools": {
                "total_calls": total_tool_calls,
                "overall_success_rate": global_tool_success_rate,
                "breakdown": {
                    name: {
                        "total_calls": m.total_calls,
                        "success_rate": m.success_rate,
                        "avg_duration_ms": m.avg_duration_ms,
                    }
                    for name, m in self._tool_metrics.items()
                },
            },
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()

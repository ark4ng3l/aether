"""
Cache & CircuitBreaker — Response Caching & Fault-Tolerant Tool Execution.

Features:
  • In-Memory TTL Cache: Prevents redundant HTTP lookups (e.g. WHOIS cached 24h, Search 1h).
  • Per-Tool Circuit Breaker: Automatically degrades tools failing 3x consecutively.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from aether.perception.tools.registry import ToolResult
from aether.core.logger import logger

# Default Cache TTLs per tool in seconds
TOOL_CACHE_TTL: Dict[str, float] = {
    "whois_lookup": 86400.0,     # 24 hours
    "ip_geolocate": 43200.0,     # 12 hours
    "network_recon": 21600.0,    # 6 hours
    "subdomain_finder": 14400.0, # 4 hours
    "breach_lookup": 86400.0,    # 24 hours
    "social_recon": 7200.0,      # 2 hours
    "web_search": 3600.0,        # 1 hour
    "shodan_lookup": 43200.0,    # 12 hours
    "github_dorker": 7200.0,     # 2 hours
    "metadata_extractor": 86400.0,
    "image_osint": 86400.0,
}
DEFAULT_CACHE_TTL = 3600.0  # 1 hour default


@dataclass
class CacheEntry:
    result: ToolResult
    expires_at: float


class ResponseCache:
    """In-memory key-value cache for tool results with per-tool TTLs and bounded capacity."""

    MAX_ENTRIES: int = 1000

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self._store: Dict[str, CacheEntry] = {}

    @staticmethod
    def _make_key(tool_name: str, params: Dict[str, Any]) -> str:
        param_str = json.dumps(params, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{tool_name}:{param_str}".encode()).hexdigest()[:16]
        return f"{tool_name}:{digest}"

    def _evict_if_needed(self):
        now = time.time()
        # 1. Purge expired keys
        expired = [k for k, v in self._store.items() if now > v.expires_at]
        for k in expired:
            del self._store[k]

        # 2. If still exceeding capacity, evict entries nearest expiration
        if len(self._store) >= self.max_entries:
            sorted_entries = sorted(self._store.items(), key=lambda item: item[1].expires_at)
            overflow = len(self._store) - self.max_entries + 1
            for k, _ in sorted_entries[:overflow]:
                del self._store[k]

    def get(self, tool_name: str, params: Dict[str, Any]) -> Optional[ToolResult]:
        key = self._make_key(tool_name, params)
        entry = self._store.get(key)
        if entry is None:
            return None

        if time.time() > entry.expires_at:
            del self._store[key]
            return None

        logger.info(f"Cache HIT for tool '{tool_name}' ({key})")
        return entry.result

    def set(self, tool_name: str, params: Dict[str, Any], result: ToolResult):
        if not result.success:
            return  # Do not cache failed results

        self._evict_if_needed()

        ttl = TOOL_CACHE_TTL.get(tool_name, DEFAULT_CACHE_TTL)
        key = self._make_key(tool_name, params)
        self._store[key] = CacheEntry(
            result=result,
            expires_at=time.time() + ttl,
        )

    def clear(self):
        self._store.clear()


@dataclass
class CircuitState:
    consecutive_failures: int = 0
    is_degraded: bool = False
    last_failure_time: float = 0.0
    degraded_reason: str = ""


class CircuitBreakerRegistry:
    """
    Monitors per-tool failures and trips to degraded status after 3 consecutive failures.
    Auto-resets after a cool-down window (default 5 minutes).
    """

    FAILURE_THRESHOLD = 3
    RESET_TIMEOUT = 300.0  # 5 minutes

    def __init__(self):
        self._states: Dict[str, CircuitState] = {}

    def is_available(self, tool_name: str) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_available, degradation_reason).
        If tool was degraded but cooldown elapsed, allows a probe retry.
        """
        state = self._states.get(tool_name)
        if state is None or not state.is_degraded:
            return True, None

        # Check cooldown
        if time.time() - state.last_failure_time > self.RESET_TIMEOUT:
            logger.info(f"CircuitBreaker half-open: probing degraded tool '{tool_name}'")
            return True, None

        return False, f"Tool '{tool_name}' is degraded ({state.degraded_reason})"

    def record_success(self, tool_name: str):
        state = self._states.get(tool_name)
        if state:
            state.consecutive_failures = 0
            state.is_degraded = False
            state.degraded_reason = ""

    def record_failure(self, tool_name: str, error: str):
        state = self._states.setdefault(tool_name, CircuitState())
        state.consecutive_failures += 1
        state.last_failure_time = time.time()

        if state.consecutive_failures >= self.FAILURE_THRESHOLD:
            state.is_degraded = True
            state.degraded_reason = f"Tripped after {state.consecutive_failures} consecutive failures: {error}"
            logger.warning(f"CIRCUIT BREAKER TRIPPED: {state.degraded_reason}")

    def get_status(self) -> Dict[str, Any]:
        return {
            name: {
                "degraded": state.is_degraded,
                "failures": state.consecutive_failures,
                "reason": state.degraded_reason,
            }
            for name, state in self._states.items()
        }


# Global instances
response_cache = ResponseCache()
circuit_breaker = CircuitBreakerRegistry()

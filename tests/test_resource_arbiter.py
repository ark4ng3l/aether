import pytest
import asyncio
from aether.core.resource_arbiter import ResourceArbiter
from aether.core.cache import ResponseCache, CircuitBreakerRegistry
from aether.core.metrics import MetricsCollector
from aether.perception.tools.registry import ToolResult


@pytest.mark.asyncio
async def test_resource_arbiter_concurrency():
    arbiter = ResourceArbiter(max_heavy_llm=1, max_light_llm=2)
    telemetry = arbiter.get_telemetry()
    assert telemetry["heavy_llm"]["limit"] == 1
    assert telemetry["light_llm"]["limit"] == 2

    active = 0
    max_active = 0

    async def worker():
        nonlocal active, max_active
        async with arbiter.throttle("heavy_llm"):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.05)
            active -= 1

    await asyncio.gather(worker(), worker(), worker())
    assert max_active == 1  # Strictly limited to 1 concurrent


def test_response_cache_hit_and_ttl():
    cache = ResponseCache()
    params = {"query": "target.com"}
    res = ToolResult(success=True, data={"found": True})

    cache.set("web_search", params, res)
    cached = cache.get("web_search", params)
    assert cached is not None
    assert cached.data == {"found": True}

    # Different params -> cache miss
    assert cache.get("web_search", {"query": "other.com"}) is None


def test_circuit_breaker_trips():
    cb = CircuitBreakerRegistry()
    cb.record_failure("test_tool", "Timeout")
    assert cb.is_available("test_tool")[0] is True

    cb.record_failure("test_tool", "Timeout 2")
    assert cb.is_available("test_tool")[0] is True

    cb.record_failure("test_tool", "Timeout 3")
    available, reason = cb.is_available("test_tool")
    assert available is False
    assert "degraded" in reason.lower()

    # Success resets breaker
    cb.record_success("test_tool")
    assert cb.is_available("test_tool")[0] is True


def test_metrics_collector():
    metrics = MetricsCollector()
    metrics.record_investigation_start()
    metrics.record_tool_execution("whois_lookup", duration_ms=120.5, success=True)
    metrics.record_tool_execution("whois_lookup", duration_ms=150.0, success=False)
    metrics.record_investigation_complete(success=True, entities_count=5)

    summary = metrics.get_summary()
    assert summary["investigations"]["completed"] == 1
    assert summary["investigations"]["total_entities_discovered"] == 5
    assert summary["tools"]["total_calls"] == 2
    assert summary["tools"]["breakdown"]["whois_lookup"]["total_calls"] == 2

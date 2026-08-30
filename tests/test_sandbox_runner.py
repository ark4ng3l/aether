"""
Tests for Subprocess Isolation and Resource Bounds in SandboxRunner.
Covers:
  1. Safe execution of Python code in isolated subprocess
  2. Infinite loop or slow script gets killed within timeout limit
  3. Module execution via run_synthesized_tool CLI entrypoint
"""

import pytest
import asyncio
import tempfile
import os
from aether.core.sandbox_runner import sandbox_runner, run_synthesized_tool, ToolExecutionError


@pytest.mark.asyncio
async def test_sandbox_runner_safe_execution():
    """Valid computation executes and returns expected JSON result."""
    code = """
def run(x, y):
    return {"sum": x + y, "product": x * y}
"""
    res = await sandbox_runner.run(code, func_name="run", params={"x": 5, "y": 7})
    assert res.get("success") is True
    data = res.get("data", {})
    assert data.get("sum") == 12
    assert data.get("product") == 35


@pytest.mark.asyncio
async def test_sandbox_runner_kills_infinite_loop_on_timeout():
    """Infinite loop is terminated by timeout without affecting parent process."""
    infinite_loop_code = """
import time
def run():
    while True:
        time.sleep(0.1)
    return {"done": True}
"""
    res = await sandbox_runner.run(infinite_loop_code, func_name="run", params={}, timeout=1.5)
    assert res.get("success") is False
    assert "timed out" in res.get("error", "").lower()


@pytest.mark.asyncio
async def test_run_synthesized_tool_cli_invocation():
    """Executes a temporary Python module via the CLI runner."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write("""
def execute(domain):
    return {"status": "analyzed", "target": domain}
""")
        mod_path = f.name

    try:
        res = await run_synthesized_tool(mod_path, params={"domain": "example.org"}, func_name="execute", timeout=5.0)
        assert isinstance(res, dict)
        assert res.get("status") == "analyzed"
        assert res.get("target") == "example.org"
    finally:
        if os.path.exists(mod_path):
            os.unlink(mod_path)

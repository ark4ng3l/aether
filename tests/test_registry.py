"""Tests for aether.perception.tools.registry — ToolRegistry and BaseTool."""

import pytest
from aether.perception.tools.registry import BaseTool, ToolResult, ToolRegistry


class DummyTool(BaseTool):
    """Minimal tool for testing."""
    def __init__(self):
        super().__init__(name="dummy", description="A test tool.")

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"echo": kwargs})


class FailingTool(BaseTool):
    def __init__(self):
        super().__init__(name="fail", description="Always fails.")

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=False, data={}, error="Intentional failure")


class TestToolResult:
    def test_success(self):
        r = ToolResult(success=True, data={"key": "value"})
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = ToolResult(success=False, data={}, error="Boom")
        assert r.success is False
        assert r.error == "Boom"


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = DummyTool()
        reg.register(tool)
        assert reg.get_tool("dummy") is tool

    def test_get_nonexistent(self):
        reg = ToolRegistry()
        assert reg.get_tool("nope") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(DummyTool())
        reg.register(FailingTool())
        tools = reg.list_tools()
        names = {t["name"] for t in tools}
        assert names == {"dummy", "fail"}

    def test_overwrite(self):
        reg = ToolRegistry()
        t1 = DummyTool()
        t2 = DummyTool()
        reg.register(t1)
        reg.register(t2)
        assert reg.get_tool("dummy") is t2


class TestBaseTool:
    @pytest.mark.asyncio
    async def test_execute(self):
        tool = DummyTool()
        result = await tool.execute(foo="bar")
        assert result.success is True
        assert result.data["echo"]["foo"] == "bar"

    @pytest.mark.asyncio
    async def test_failing_tool(self):
        tool = FailingTool()
        result = await tool.execute()
        assert result.success is False
        assert result.error == "Intentional failure"

    @pytest.mark.asyncio
    async def test_base_not_implemented(self):
        base = BaseTool(name="base", description="Abstract")
        with pytest.raises(NotImplementedError):
            await base.execute()

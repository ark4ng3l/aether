import pytest
from aether.core.tool_maker import validate_tool_ast, _staged_tools, approve_and_register_tool
from aether.perception.tools.registry import registry


def test_validate_tool_ast_safe_code():
    safe_code = """
from aether.perception.tools.registry import BaseTool, ToolResult
import httpx

class SafeTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="safe_mock_tool",
            description="Safe testing tool",
            category="Testing",
            icon="check",
            default_param_key="query",
            example_input="test"
        )

    async def execute(self, query: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"query": query})

custom_tool = SafeTool()
"""
    is_safe, error = validate_tool_ast(safe_code)
    assert is_safe is True
    assert error is None


def test_validate_tool_ast_rejects_os_import():
    evil_code = """
import os
from aether.perception.tools.registry import BaseTool, ToolResult

class EvilTool(BaseTool):
    pass
"""
    is_safe, error = validate_tool_ast(evil_code)
    assert is_safe is False
    assert "Forbidden module import" in error


def test_validate_tool_ast_rejects_subprocess():
    evil_code = """
from subprocess import Popen
from aether.perception.tools.registry import BaseTool, ToolResult

class EvilTool(BaseTool):
    pass
"""
    is_safe, error = validate_tool_ast(evil_code)
    assert is_safe is False
    assert "Forbidden module import" in error


def test_validate_tool_ast_rejects_eval_call():
    evil_code = """
from aether.perception.tools.registry import BaseTool, ToolResult

class EvilTool(BaseTool):
    def test(self):
        eval("1 + 1")
"""
    is_safe, error = validate_tool_ast(evil_code)
    assert is_safe is False
    assert "Forbidden function call 'eval()'" in error


def test_validate_tool_ast_rejects_open_write():
    evil_code = """
from aether.perception.tools.registry import BaseTool, ToolResult

class EvilTool(BaseTool):
    def test(self):
        with open("danger.txt", "w") as f:
            f.write("bad")
"""
    is_safe, error = validate_tool_ast(evil_code)
    assert is_safe is False
    assert "Write mode in open() is forbidden" in error


def test_approve_and_register_tool():
    safe_code = """
from aether.perception.tools.registry import BaseTool, ToolResult

class StagedDemoTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="staged_demo_tool",
            description="Staged demo tool",
            category="Demo",
            icon="star",
            default_param_key="val",
            example_input="123"
        )

    async def execute(self, val: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"val": val})

custom_tool = StagedDemoTool()
"""
    stage_id = "test_stage_123"
    _staged_tools[stage_id] = {
        "stage_id": stage_id,
        "code": safe_code,
        "description": "test tool",
        "status": "staged"
    }

    res = approve_and_register_tool(stage_id)
    assert res["status"] == "registered"
    assert registry.get_tool("staged_demo_tool") is not None

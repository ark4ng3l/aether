"""
Dynamic Tool Registry for AETHER perception and OSINT capabilities.
"""

from __future__ import annotations

import asyncio
import datetime
from typing import List, Callable, Any, Dict, Optional
from pydantic import BaseModel
from aether.core.logger import logger


class ToolResult(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class BaseTool:
    """Base class for all AETHER perception and OSINT tools."""

    def __init__(
        self,
        name: str,
        description: str,
        category: str = "General OSINT",
        icon: str = "build",
        default_param_key: str = "query",
        example_input: str = "example.com",
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.icon = icon
        self.default_param_key = default_param_key
        self.example_input = example_input
        self.params = params or {}
        self.is_dynamic = False
        self.registered_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    async def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError("All tools must implement the execute method.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "default_param_key": self.default_param_key,
            "example_input": self.example_input,
            "params": self.params,
            "is_dynamic": self.is_dynamic,
            "registered_at": self.registered_at,
            "status": "ready",
        }


class ToolRegistry:
    """Dynamic registry for tool discovery by the reasoning engine."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} [{tool.category}]")

    def unregister(self, name: str) -> bool:
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]


# Global registry instance
registry = ToolRegistry()


class FunctionTool(BaseTool):
    """Wraps a standard callable function into an AETHER BaseTool."""

    def __init__(self, func: Callable, name: Optional[str] = None, category: str = "Specialized OSINT", description: Optional[str] = None):
        t_name = name or func.__name__
        t_desc = description or (func.__doc__ or "Specialized AETHER analytical tool").strip()
        super().__init__(name=t_name, description=t_desc, category=category)
        self.func = func

    async def execute(self, **kwargs) -> ToolResult:
        import time
        t0 = time.time()
        try:
            if asyncio.iscoroutinefunction(self.func):
                res = await self.func(**kwargs)
            else:
                res = self.func(**kwargs)
            elapsed = round((time.time() - t0) * 1000, 2)
            if isinstance(res, dict) and "success" in res:
                return ToolResult(
                    success=res.get("success", True),
                    data=res,
                    error=res.get("error"),
                    execution_time_ms=elapsed,
                )
            return ToolResult(success=True, data=res, execution_time_ms=elapsed)
        except Exception as exc:
            elapsed = round((time.time() - t0) * 1000, 2)
            return ToolResult(success=False, data=None, error=str(exc), execution_time_ms=elapsed)


def register_tool(func_or_tool: Any, category: str = "Specialized OSINT"):
    """Decorator or function to register a tool into the global registry."""
    if isinstance(func_or_tool, BaseTool):
        registry.register(func_or_tool)
        return func_or_tool

    # Otherwise wrap function
    tool_instance = FunctionTool(func=func_or_tool, category=category)
    registry.register(tool_instance)
    return func_or_tool

import asyncio
from typing import List, Callable, Any, Dict, Optional
from pydantic import BaseModel
from aether.core.logger import logger

class ToolResult(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None

class BaseTool:
    """Base class for all AETHER tools."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError("All tools must implement the execute method.")

class ToolRegistry:
    """Dynamic registry for tool discovery by the reasoning engine."""
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

# Global registry instance
registry = ToolRegistry()

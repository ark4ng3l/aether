"""
BaseSpecialist — Abstract Base Class for Specialist Agents in AETHER v4.0.
Specialists encapsulate specific domain skills (Network, Vision, Audio, Toolmaker).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from aether.core.logger import logger
from aether.perception.tools.registry import BaseTool, ToolResult, registry


class SpecialistResult(BaseModel):
    specialist_name: str
    instruction: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    error: Optional[str] = None


class BaseSpecialist(ABC):
    """Abstract plugin base class for specialized domain agents."""

    def __init__(self, name: str, domain: str, description: str):
        self.name = name
        self.domain = domain
        self.description = description

    @abstractmethod
    async def execute_specialized_task(
        self,
        instruction: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes domain-specific actions using assigned tools and models.
        Must return:
            {"success": bool, "data": dict, "summary": str, "error": Optional[str]}
        """
        pass

    def __repr__(self) -> str:
        return f"<Specialist: {self.name} [{self.domain}]>"

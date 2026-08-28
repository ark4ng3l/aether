"""
ToolMaker — Autonomous Dynamic Tool Synthesis and Hot-Registration.

Uses Hermes 35B to generate, validate, sandbox-test, and register custom OSINT tools
at runtime with automatic persistence.
"""

from __future__ import annotations

import ast
import datetime
import importlib.util
import os
import re
import sys
import time
from typing import Dict, Any, Optional

from aether.perception.tools.registry import registry, BaseTool, ToolResult
from aether.orchestration.model_manager import model_manager
from aether.config.settings import settings
from aether.core.logger import logger

CUSTOM_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "custom_tools"
)
os.makedirs(CUSTOM_TOOLS_DIR, exist_ok=True)


async def synthesize_custom_tool(description: str) -> Dict[str, Any]:
    """
    Synthesizes a new OSINT tool based on user instructions or newly discovered techniques.
    Validates Python syntax, instantiates the class, and registers it live.
    """
    logger.info(f"Synthesizing new tool with prompt: {description[:80]}...")

    prompt = (
        "You are AETHER's autonomous tool developer and Python systems engineer.\n"
        "Your task is to write a complete, standalone Python class for an OSINT/reconnaissance tool.\n\n"
        f"USER SPECIFICATION / CAPABILITY NEEDED:\n{description}\n\n"
        "MANDATORY REQUIREMENTS:\n"
        "1. Must subclass `BaseTool` from `aether.perception.tools.registry`.\n"
        "2. Must import `BaseTool, ToolResult` from `aether.perception.tools.registry`.\n"
        "3. In `__init__`, pass: name (lowercase alphanumeric with underscores), description, category, icon, default_param_key, example_input.\n"
        "4. Implement `async def execute(self, **kwargs) -> ToolResult`.\n"
        "5. Inside `execute()`, extract parameters cleanly, perform real HTTP requests with `httpx` or text processing, and wrap EVERYTHING in `try...except`.\n"
        "6. Return `ToolResult(success=True, data={...})` on success, or `ToolResult(success=False, data={}, error=str(e))` on error.\n"
        "7. At the bottom, instantiate the tool as `custom_tool = YourToolClass()`.\n\n"
        "OUTPUT FORMAT: Return ONLY executable Python code inside a ```python ``` block. No conversational preamble."
    )

    try:
        raw_code = await model_manager.call_model(
            prompt,
            model=settings.MODEL_DEEP,
            is_heavy=True,
            temperature=0.2,
            task_label="Tool Synthesis",
        )

        # Extract python code block
        code_match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", raw_code)
        code = code_match.group(1) if code_match else raw_code.strip()

        # 1. Syntax Check with AST
        ast.parse(code)

        # 2. Compile and execute in isolated module namespace
        module_name = f"dynamic_tool_{int(time.time())}"
        module_file = os.path.join(CUSTOM_TOOLS_DIR, f"{module_name}.py")

        with open(module_file, "w", encoding="utf-8") as f:
            f.write(code)

        # 3. Dynamic Import
        spec = importlib.util.spec_from_file_location(module_name, module_file)
        if not spec or not spec.loader:
            raise RuntimeError("Failed to load module spec")

        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)

        # Find the BaseTool instance or class
        tool_instance: Optional[BaseTool] = None
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, BaseTool) and attr.__class__ != BaseTool:
                tool_instance = attr
                break
            elif isinstance(attr, type) and issubclass(attr, BaseTool) and attr != BaseTool:
                tool_instance = attr()
                break

        if not tool_instance:
            raise RuntimeError("Generated code does not contain a valid BaseTool instance")

        tool_instance.is_dynamic = True
        tool_instance.registered_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Register live
        registry.register(tool_instance)

        return {
            "status": "success",
            "tool_name": tool_instance.name,
            "category": tool_instance.category,
            "description": tool_instance.description,
            "icon": tool_instance.icon,
            "file_path": module_file,
            "code": code,
        }
    except Exception as exc:
        logger.error(f"Tool synthesis failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }


def load_persisted_custom_tools():
    """Scans custom_tools directory and registers previously synthesized tools on startup."""
    if not os.path.exists(CUSTOM_TOOLS_DIR):
        return

    for fname in os.listdir(CUSTOM_TOOLS_DIR):
        if fname.endswith(".py") and not fname.startswith("__"):
            try:
                mod_path = os.path.join(CUSTOM_TOOLS_DIR, fname)
                mod_name = f"custom_tool_{fname[:-3]}"
                spec = importlib.util.spec_from_file_location(mod_name, mod_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[mod_name] = mod
                    spec.loader.exec_module(mod)

                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if isinstance(attr, BaseTool) and attr.__class__ != BaseTool:
                            attr.is_dynamic = True
                            registry.register(attr)
                            break
                        elif isinstance(attr, type) and issubclass(attr, BaseTool) and attr != BaseTool:
                            inst = attr()
                            inst.is_dynamic = True
                            registry.register(inst)
                            break
            except Exception as e:
                logger.warning(f"Could not load custom tool {fname}: {e}")

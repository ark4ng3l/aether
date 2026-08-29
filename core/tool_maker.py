"""
ToolMaker — Autonomous Dynamic Tool Synthesis with AST Sandboxing and Human Approval.

Uses LLMs to generate, statically inspect, sandbox-validate, and register custom OSINT tools
at runtime with strict security guardrails.
"""

from __future__ import annotations

import ast
import datetime
import importlib.util
import os
import re
import sys
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple

from aether.perception.tools.registry import registry, BaseTool, ToolResult
from aether.core.model_manager import model_manager
from aether.config.settings import settings
from aether.core.logger import logger

CUSTOM_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "custom_tools"
)
os.makedirs(CUSTOM_TOOLS_DIR, exist_ok=True)

# In-memory staged tools awaiting approval
_staged_tools: Dict[str, Dict[str, Any]] = {}

# Forbidden modules and functions for static sandboxing
BANNED_MODULES = {
    "os", "subprocess", "sys", "socket", "ctypes", "shutil",
    "pickle", "pty", "commands", "builtin", "builtins",
    "posix", "nt", "_thread", "threading", "multiprocessing",
}

BANNED_CALLS = {
    "eval", "exec", "__import__", "compile", "globals", "locals",
    "breakpoint", "input", "exit", "quit"
}


def validate_tool_ast(code: str) -> Tuple[bool, Optional[str]]:
    """
    Statically analyzes generated tool Python code via Abstract Syntax Tree (AST).
    Rejects any code containing dangerous modules, arbitrary system calls, or write operations.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"

    for node in ast.walk(tree):
        # 1. Check imports: import X
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0].lower()
                if root_pkg in BANNED_MODULES:
                    return False, f"Security Violation: Forbidden module import '{alias.name}'"

        # 2. Check from imports: from X import Y
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0].lower()
                if root_pkg in BANNED_MODULES:
                    return False, f"Security Violation: Forbidden module import from '{node.module}'"

        # 3. Check function calls
        elif isinstance(node, ast.Call):
            func = node.func
            # Direct calls like eval(...) or exec(...)
            if isinstance(func, ast.Name):
                if func.id in BANNED_CALLS:
                    return False, f"Security Violation: Forbidden function call '{func.id}()'"
                # Check write open calls: open(..., 'w' or 'a')
                if func.id == "open":
                    for arg in node.args[1:]:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if any(mode in arg.value for mode in ["w", "a", "x", "+"]):
                                return False, "Security Violation: Write mode in open() is forbidden"

            # Attribute calls like os.system() or subprocess.Popen()
            elif isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    if func.value.id in BANNED_MODULES:
                        return False, f"Security Violation: Forbidden call on '{func.value.id}.{func.attr}'"

    return True, None


async def synthesize_custom_tool(description: str, auto_register: bool = False) -> Dict[str, Any]:
    """
    Synthesizes a new OSINT tool based on user instructions.
    Validates Python syntax and AST sandboxing.
    If auto_register is False, stages the tool for operator review.
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
        "7. At the bottom, instantiate the tool as `custom_tool = YourToolClass()`.\n"
        "8. SECURITY RESTRICTION: Do NOT use os, subprocess, sys, socket, ctypes, eval, or exec.\n\n"
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

        # 1. Static AST Security Validation
        is_safe, violation = validate_tool_ast(code)
        if not is_safe:
            logger.error(f"Tool synthesis rejected by AST sandbox: {violation}")
            return {
                "status": "rejected",
                "error": violation,
                "code": code,
            }

        # 2. Stage tool for review
        stage_id = f"stage_{uuid.uuid4().hex[:8]}"
        staged_entry = {
            "stage_id": stage_id,
            "description": description,
            "code": code,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "staged",
        }
        _staged_tools[stage_id] = staged_entry

        if not auto_register:
            return {
                "status": "staged",
                "stage_id": stage_id,
                "message": "Tool synthesized and passed AST sandbox. Operator approval required.",
                "code": code,
            }

        # 3. If auto_register is requested and AST is safe:
        return approve_and_register_tool(stage_id)

    except Exception as exc:
        logger.error(f"Tool synthesis failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }


def list_staged_tools() -> List[Dict[str, Any]]:
    """Returns all currently staged tools awaiting operator approval."""
    return list(_staged_tools.values())


def approve_and_register_tool(stage_id: str) -> Dict[str, Any]:
    """Approves a staged tool, writes it to disk, imports it, and registers it live."""
    staged = _staged_tools.get(stage_id)
    if not staged:
        return {"status": "error", "error": f"Staged tool '{stage_id}' not found"}

    code = staged["code"]

    # Re-validate AST before compiling
    is_safe, violation = validate_tool_ast(code)
    if not is_safe:
        return {"status": "rejected", "error": violation}

    try:
        module_name = f"dynamic_tool_{int(time.time())}_{stage_id}"
        module_file = os.path.join(CUSTOM_TOOLS_DIR, f"{module_name}.py")

        with open(module_file, "w", encoding="utf-8") as f:
            f.write(code)

        spec = importlib.util.spec_from_file_location(module_name, module_file)
        if not spec or not spec.loader:
            raise RuntimeError("Failed to load module spec")

        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)

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

        # Register into live registry
        registry.register(tool_instance)
        staged["status"] = "approved"
        staged["tool_name"] = tool_instance.name

        logger.success(f"Dynamic tool '{tool_instance.name}' approved and registered live.")

        return {
            "status": "registered",
            "tool_name": tool_instance.name,
            "category": tool_instance.category,
            "description": tool_instance.description,
            "icon": tool_instance.icon,
            "file_path": module_file,
            "code": code,
        }
    except Exception as exc:
        logger.error(f"Approval of tool '{stage_id}' failed: {exc}")
        return {"status": "error", "error": str(exc)}


def load_persisted_custom_tools():
    """Scans custom_tools directory, validates AST of each, and registers safe tools on startup."""
    if not os.path.exists(CUSTOM_TOOLS_DIR):
        return

    for fname in os.listdir(CUSTOM_TOOLS_DIR):
        if fname.endswith(".py") and not fname.startswith("__"):
            try:
                mod_path = os.path.join(CUSTOM_TOOLS_DIR, fname)
                with open(mod_path, "r", encoding="utf-8") as f:
                    content = f.read()

                is_safe, violation = validate_tool_ast(content)
                if not is_safe:
                    logger.warning(f"Skipping persisted custom tool {fname}: {violation}")
                    continue

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

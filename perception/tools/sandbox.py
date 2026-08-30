"""
ASTCodeSandbox — Abstract Syntax Tree (AST) Security Sandbox for Dynamic Toolmaker.
Enforces strict policy rules on LLM-synthesized Python code before compilation and execution.
"""

from __future__ import annotations

import ast
from typing import Dict, Any, Tuple, Optional, Set
from aether.core.logger import logger


class SecurityPolicyViolation(Exception):
    """Raised when dynamically generated Python code violates the AST security sandbox policy."""
    pass


class ASTCodeSandbox:
    """
    Abstract Syntax Tree (AST) Security Sandbox.
    Inspects synthesized Python AST nodes to ensure generated tools perform only
    benign network/data-parsing operations without host-system escapes.
    """

    # Prohibited modules that cannot be imported
    DISALLOWED_MODULES: Set[str] = {
        "os", "sys", "subprocess", "shutil", "builtins",
        "ctypes", "pty", "commands", "pickle", "socketserver",
        "multiprocessing", "threading", "importlib", "signal",
        "winreg", "posix", "_winapi",
    }

    # Prohibited dangerous built-in functions
    DISALLOWED_CALLS: Set[str] = {
        "eval", "exec", "compile", "__import__", "open",
        "breakpoint", "memoryview", "globals", "locals",
        "getattr", "setattr", "delattr",
    }

    @classmethod
    def validate_source(cls, source_code: str) -> Tuple[bool, Optional[str]]:
        """
        Walks the Abstract Syntax Tree (AST) of the Python source code.
        Returns:
            (is_safe: bool, error_reason: Optional[str])
        """
        if not source_code or not source_code.strip():
            return False, "Source code is empty"

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return False, f"Syntax Error: {e.msg} at line {e.lineno}"

        for node in ast.walk(tree):
            # 1. Audit Import statements
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0].lower()
                    if root_pkg in cls.DISALLOWED_MODULES:
                        return False, f"Prohibited import statement: '{alias.name}'"

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0].lower()
                    if root_pkg in cls.DISALLOWED_MODULES:
                        return False, f"Prohibited from-import statement: '{node.module}'"

            # 2. Audit Function and Method Calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.DISALLOWED_CALLS:
                        return False, f"Prohibited call to dangerous function: '{node.func.id}()'"

            # 3. Audit Access to Private/Internal Dunder Attributes
            elif isinstance(node, ast.Attribute):
                attr_name = node.attr
                if attr_name.startswith("__") and attr_name.endswith("__"):
                    if attr_name not in {"__init__", "__name__", "__doc__"}:
                        return False, f"Prohibited access to internal dunder attribute: '{attr_name}'"

        return True, None

    @classmethod
    def execute_sandboxed_tool(
        cls,
        source_code: str,
        entrypoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validates source code via AST, compiles into isolated bytecode,
        and executes with a hardened global namespace.
        """
        is_safe, error_msg = cls.validate_source(source_code)
        if not is_safe:
            logger.warning(f"AST Sandbox blocked execution: {error_msg}")
            raise SecurityPolicyViolation(f"Sandbox rejection: {error_msg}")

        # Safe import wrapper to allow benign stdlib imports (e.g. hashlib, json, re, ipaddress)
        # while strictly enforcing disallowed module blacklist at runtime.
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            root_mod = name.split(".")[0]
            if root_mod in cls.DISALLOWED_MODULES or name in cls.DISALLOWED_MODULES:
                raise SecurityPolicyViolation(f"Runtime import of prohibited module '{name}' is blocked.")
            return __import__(name, globals, locals, fromlist, level)

        # Construct hardened execution environment
        safe_builtins = {
            "dict": dict, "list": list, "set": set, "tuple": tuple,
            "str": str, "int": int, "float": float, "bool": bool,
            "len": len, "range": range, "enumerate": enumerate,
            "zip": zip, "min": min, "max": max, "sum": sum, "round": round,
            "sorted": sorted, "reversed": reversed, "any": any, "all": all,
            "isinstance": isinstance, "issubclass": issubclass,
            "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
            "KeyError": KeyError, "AttributeError": AttributeError,
            "__import__": safe_import,
        }

        execution_scope: Dict[str, Any] = {
            "__builtins__": safe_builtins,
            "__name__": "__dynamic_tool__",
        }

        try:
            compiled_code = compile(source_code, filename="<dynamic_tool>", mode="exec")
            exec(compiled_code, execution_scope)
        except Exception as exc:
            logger.error(f"Compilation/execution error in dynamic tool: {exc}")
            raise

        target_func = execution_scope.get(entrypoint)
        if not callable(target_func):
            raise AttributeError(f"Entrypoint '{entrypoint}' not found or is not callable in synthesized code.")

        try:
            return target_func(**params)
        except Exception as exc:
            logger.error(f"Runtime error in dynamic tool '{entrypoint}': {exc}")
            raise

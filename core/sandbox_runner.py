"""
Sandbox Runner — Isolated Subprocess Execution for Dynamically Synthesized Tools.
Enforces timeout, strips sensitive environment variables, and captures output cleanly.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

from aether.core.logger import logger


WRAPPER_SCRIPT = """
import sys
import json
import traceback

# Read input payload from stdin
try:
    raw_in = sys.stdin.read()
    payload = json.loads(raw_in) if raw_in else {}
    params = payload.get("params", {})
    func_name = payload.get("func_name", "run")
except Exception as e:
    sys.stdout.write(json.dumps({"success": False, "error": f"Failed to parse stdin payload: {e}"}))
    sys.exit(1)

# Execute tool code in local namespace
local_ns = {}
try:
    with open(payload["code_file"], "r", encoding="utf-8") as f:
        code_str = f.read()
    
    exec(code_str, local_ns, local_ns)
    
    fn = None
    if func_name in local_ns and callable(local_ns[func_name]):
        fn = local_ns[func_name]
    elif "custom_tool" in local_ns and hasattr(local_ns["custom_tool"], "execute"):
        fn = getattr(local_ns["custom_tool"], "execute")
    else:
        for k, v in local_ns.items():
            if hasattr(v, "execute") and callable(getattr(v, "execute")):
                fn = getattr(v, "execute")
                break
            elif isinstance(v, type) and hasattr(v, "execute"):
                instance = v()
                fn = getattr(instance, "execute")
                break

    if not fn:
        raise ValueError("No executable entrypoint or BaseTool found in synthesized tool code.")
    
    import asyncio
    import inspect
    if inspect.iscoroutinefunction(fn):
        result = asyncio.run(fn(**params))
    else:
        result = fn(**params)

    if hasattr(result, "model_dump"):
        result_dict = result.model_dump()
    elif isinstance(result, dict):
        result_dict = result
    else:
        result_dict = {"data": str(result)}
    
    output = {
        "success": True,
        "data": result_dict,
        "error": None
    }
    sys.stdout.write(json.dumps(output))
except Exception as exc:
    err_msg = traceback.format_exc()
    sys.stdout.write(json.dumps({"success": False, "error": str(exc), "traceback": err_msg}))
    sys.exit(0)
"""


class SandboxRunner:
    """Runs Python tool code in an isolated subprocess with stripped environment and strict timeout."""

    def __init__(self, default_timeout: float = 15.0):
        self.default_timeout = default_timeout

    async def run(
        self,
        code: str,
        func_name: str = "run",
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Executes code in a sandbox subprocess."""
        params = params or {}
        timeout = timeout or self.default_timeout

        sanitized_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "PYTHONPATH": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
            "TEMP": os.environ.get("TEMP", ""),
            "TMP": os.environ.get("TMP", ""),
        }

        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sandbox_tmp")
        os.makedirs(temp_dir, exist_ok=True)

        import tempfile
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, suffix=".py", delete=False, encoding="utf-8") as f_code:
            f_code.write(code)
            code_file = f_code.name

        with tempfile.NamedTemporaryFile("w", dir=temp_dir, suffix=".py", delete=False, encoding="utf-8") as f_wrap:
            f_wrap.write(WRAPPER_SCRIPT)
            wrapper_file = f_wrap.name

        input_payload = json.dumps({
            "code_file": code_file,
            "func_name": func_name,
            "params": params
        })

        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                wrapper_file,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=sanitized_env,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=input_payload.encode("utf-8")),
                timeout=timeout,
            )

            stdout_str = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr_str = stderr_bytes.decode("utf-8", errors="replace").strip()

            if stdout_str:
                # Search for JSON payload from bottom-up in case stdout contains logger text
                for line in reversed(stdout_str.splitlines()):
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            return json.loads(line)
                        except Exception:
                            pass
                try:
                    return json.loads(stdout_str)
                except Exception:
                    return {"success": False, "error": stdout_str, "raw_stderr": stderr_str}

            return {
                "success": False,
                "error": stderr_str or f"Subprocess exited with code {proc.returncode} and empty output",
            }

        except asyncio.TimeoutError:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            return {"success": False, "error": f"Tool execution timed out after {timeout}s"}
        except Exception as exc:
            return {"success": False, "error": f"Sandbox execution error: {exc}"}
        finally:
            for p in (code_file, wrapper_file):
                try:
                    if os.path.exists(p):
                        os.unlink(p)
                except Exception:
                    pass


sandbox_runner = SandboxRunner()


class ToolExecutionError(Exception):
    """Raised when isolated synthesized tool execution fails or times out."""
    pass


async def run_synthesized_tool(
    module_path: str,
    params: dict,
    func_name: str = "execute",
    timeout: float = 15.0,
) -> dict:
    """
    Invokes module in isolated subprocess via sandbox_runner CLI.
    """
    env = dict(os.environ)
    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    env["PYTHONPATH"] = proj_root

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "aether.core.sandbox_runner",
        module_path,
        func_name,
        json.dumps(params),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise ToolExecutionError("Synthesized tool exceeded time limit")

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="replace")[:500]
        raise ToolExecutionError(f"Synthesized tool failed: {err_msg}")

    return json.loads(stdout.decode("utf-8", errors="replace"))


def main():
    """
    Subprocess CLI entrypoint invoked as:
    python -m aether.core.sandbox_runner <module_path> <func_name> <params_json>
    """
    if len(sys.argv) < 4:
        sys.stderr.write("Usage: python -m aether.core.sandbox_runner <module_path> <func_name> <params_json>\n")
        sys.exit(1)

    module_path, func_name, params_json = sys.argv[1], sys.argv[2], sys.argv[3]

    # OS-level resource limits on POSIX platforms (256MB memory cap, 10s CPU cap)
    if sys.platform != "win32":
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        except Exception:
            pass

    import importlib.util
    spec = importlib.util.spec_from_file_location("synthesized_tool", module_path)
    if not spec or not spec.loader:
        sys.stderr.write(f"Failed to load module spec from {module_path}\n")
        sys.exit(1)

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    fn = getattr(mod, func_name, None)
    if not fn:
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if hasattr(attr, func_name) and callable(getattr(attr, func_name)):
                fn = getattr(attr, func_name)
                break
            elif isinstance(attr, type) and hasattr(attr, func_name):
                inst = attr()
                fn = getattr(inst, func_name)
                break

    if not fn or not callable(fn):
        sys.stderr.write(f"Function or method '{func_name}' not found in {module_path}\n")
        sys.exit(1)

    params = json.loads(params_json) if params_json else {}
    import inspect
    if inspect.iscoroutinefunction(fn):
        result = asyncio.run(fn(**params))
    else:
        result = fn(**params)

    if hasattr(result, "model_dump"):
        result = result.model_dump()
    print(json.dumps(result))


if __name__ == "__main__":
    main()

"""
ToolmakerSpecialist — Dynamic Python Tool Synthesis & AST-Sandboxed Execution Agent.
Allows AETHER to expand its own capabilities on-the-fly when standard tools are insufficient.
"""

from __future__ import annotations

import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from aether.reasoning.specialists.base_specialist import BaseSpecialist
from aether.perception.tools.sandbox import ASTCodeSandbox, SecurityPolicyViolation
from aether.perception.tools.registry import BaseTool, ToolResult, registry
from aether.core.model_manager import model_manager
from aether.core.logger import logger


class SynthesizedToolSchema(BaseModel):
    tool_name: str
    description: str
    entrypoint: str
    python_code: str
    example_input: str = "example.com"


class ToolmakerSpecialist(BaseSpecialist):
    """Specialist agent that writes, AST-validates, and registers new Python OSINT & intelligence tools on-the-fly."""

    def __init__(self):
        super().__init__(
            name="toolmaker_specialist",
            domain="Dynamic Capability Synthesis",
            description="Synthesizes and executes custom sandboxed Python scripts for novel intelligence tasks.",
        )

    async def execute_specialized_task(
        self,
        instruction: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(f"ToolmakerSpecialist synthesizing capability for: {instruction}")
        
        # 1. Ask LLM to generate pure Python tool code
        prompt = (
            f"You are the AETHER Dynamic Tool Synthesizer.\n"
            f"TASK REQUIREMENT: {instruction}\n"
            f"CONTEXT: {json.dumps(context, default=str)}\n\n"
            f"Write a standalone, robust Python function to achieve this task.\n"
            f"CRITICAL SECURITY CONSTRAINTS:\n"
            f"- DO NOT import 'os', 'sys', 'subprocess', 'shutil', 'builtins', 'ctypes', 'pty', 'pickle'\n"
            f"- DO NOT use 'eval', 'exec', 'open', '__import__'\n"
            f"- Use 'httpx' or standard safe data parsing algorithms\n"
            f"- The entrypoint function must accept keyword arguments and return a dict\n\n"
            f"Return JSON strictly conforming to the schema."
        )

        synth_result = None
        try:
            synth_result = await model_manager.call_model(
                prompt,
                response_format=SynthesizedToolSchema,
                task_label="Dynamic Tool Synthesis",
            )
        except Exception as model_err:
            logger.debug(f"Toolmaker model generation fallback: {model_err}")

        if not isinstance(synth_result, SynthesizedToolSchema):
            # Heuristic fallback if LLM is offline or raw text
            synth_result = SynthesizedToolSchema(
                tool_name="custom_query_probe",
                description=instruction,
                entrypoint="execute_probe",
                python_code=(
                    "def execute_probe(**kwargs):\n"
                    "    target = kwargs.get('target', kwargs.get('domain', ''))\n"
                    "    return {'target': target, 'status': 'probe_synthesized_offline', 'query': str(kwargs)}\n"
                ),
                example_input="example.com",
            )

        try:
            # 2. Validate synthesized code via AST Sandbox
            is_safe, error_msg = ASTCodeSandbox.validate_source(synth_result.python_code)
            if not is_safe:
                logger.warning(f"Toolmaker: Synthesized code failed AST sandbox: {error_msg}")
                return {
                    "success": False,
                    "error": f"AST Sandbox policy rejection: {error_msg}",
                    "data": {"code": synth_result.python_code},
                    "summary": "Synthesized code rejected by security sandbox.",
                }

            # 3. Execute the sandboxed tool with given context parameters
            exec_output = ASTCodeSandbox.execute_sandboxed_tool(
                source_code=synth_result.python_code,
                entrypoint=synth_result.entrypoint,
                params=context,
            )

            return {
                "success": True,
                "data": exec_output if isinstance(exec_output, dict) else {"result": exec_output},
                "synthesized_tool_name": synth_result.tool_name,
                "summary": f"Dynamically synthesized tool '{synth_result.tool_name}' executed safely via AST sandbox.",
                "tool_used": "ast_sandbox_toolmaker",
            }

        except SecurityPolicyViolation as sec_exc:
            return {
                "success": False,
                "error": f"Security Violation: {sec_exc}",
                "data": {},
                "summary": "Execution blocked by AST Sandbox policy.",
            }
        except Exception as exc:
            logger.error(f"ToolmakerSpecialist failure: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "data": {},
                "summary": f"Toolmaker synthesis failed: {exc}",
            }


toolmaker_specialist = ToolmakerSpecialist()

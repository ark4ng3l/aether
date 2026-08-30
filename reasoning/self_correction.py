"""
SelfCorrectionEngine — Automated Backtracking & Adversarial Refinement for AETHER v4.0.
Refines tasks when the Critic rejects output or identifies false positives / weak evidence.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from aether.core.logger import logger
from aether.core.model_manager import model_manager


class SelfCorrectionPlan(BaseModel):
    root_cause: str = Field(description="Analysis of why the original action failed or was refuted")
    adjustment_strategy: str = Field(description="parameter_refinement | tool_pivot | query_broadening")
    revised_instruction: str = Field(description="Updated instruction for the specialist")
    revised_inputs: Dict[str, Any] = Field(default_factory=dict)


class SelfCorrectionEngine:
    """Coordinates reflection, prompt refinement, and parameter tuning when Critic rejects output."""

    @staticmethod
    async def formulate_correction(
        task_instruction: str,
        failed_output: Dict[str, Any],
        critic_reasoning: str,
        context: Dict[str, Any],
    ) -> SelfCorrectionPlan:
        """
        Synthesizes an adjusted strategy based on the Critic's refutation.
        """
        logger.info(f"SelfCorrectionEngine analyzing refutation: {critic_reasoning}")

        prompt = (
            f"You are the AETHER Self-Correction Engine.\n"
            f"FAILED TASK: {task_instruction}\n"
            f"ORIGINAL INPUTS: {context}\n"
            f"SPECIALIST OUTPUT: {failed_output}\n"
            f"CRITIC REFUTATION/REJECTION REASON: {critic_reasoning}\n\n"
            f"Analyze why the finding was rejected (e.g. false positive, wrong parameter, service block) "
            f"and generate a refined execution plan."
        )

        try:
            plan = await model_manager.call_model(
                prompt,
                response_format=SelfCorrectionPlan,
                task_label="Self-Correction Refinement",
            )
            if isinstance(plan, SelfCorrectionPlan):
                return plan
        except Exception as exc:
            logger.warning(f"Fallback heuristic self-correction: {exc}")

        # Deterministic fallback adjustment
        return SelfCorrectionPlan(
            root_cause="Critic rejected evidence as ambiguous or unverified",
            adjustment_strategy="parameter_refinement",
            revised_instruction=f"Refine search and verify authoritative indicators for: {task_instruction}",
            revised_inputs={**context, "strict_verification": True},
        )


self_correction_engine = SelfCorrectionEngine()

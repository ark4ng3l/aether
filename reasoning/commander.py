"""
CommanderAgent — Hierarchical Master Planner & ReAct Orchestrator for AETHER v4.0.
Coordinates Tree-of-Thought task decomposition, specialist dispatching, Critic verification, and Self-Correction.
"""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from aether.core.state import AgentState, InvestigationStatus, Entity, EntityType
from aether.core.logger import logger
from aether.core.model_manager import model_manager
from aether.reasoning.critic import RedTeamCritic
from aether.reasoning.self_correction import self_correction_engine, SelfCorrectionPlan
from aether.reasoning.self_healing import self_healing_engine, FaultDiagnosis, HealingAction
from aether.reasoning.specialists.base_specialist import BaseSpecialist
from aether.reasoning.specialists.network_specialist import network_specialist
from aether.reasoning.specialists.vision_specialist import vision_specialist
from aether.reasoning.specialists.audio_specialist import audio_specialist
from aether.reasoning.specialists.toolmaker_specialist import toolmaker_specialist
from aether.memory.hybrid_store import HybridKnowledgeStore


class SubTaskPlan(BaseModel):
    task_id: str
    specialist: str = Field(description="network_specialist | vision_specialist | audio_specialist | toolmaker_specialist")
    instruction: str
    context_inputs: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    retry_count: int = 0


class PlanTreeDecomposition(BaseModel):
    goal_summary: str
    tree_reasoning: str
    subtasks: List[SubTaskPlan]


class CommanderAgent:
    """
    Commander Agent: Master orchestrator responsible for goal decomposition,
    Tree-of-Thought branch evaluation, specialist coordination, and state convergence.
    """

    def __init__(
        self,
        state: AgentState,
        specialists: Optional[Dict[str, BaseSpecialist]] = None,
        hybrid_memory: Optional[HybridKnowledgeStore] = None,
    ):
        self.state = state
        self.specialists = specialists or {
            "network_specialist": network_specialist,
            "vision_specialist": vision_specialist,
            "audio_specialist": audio_specialist,
            "toolmaker_specialist": toolmaker_specialist,
        }
        self.critic = RedTeamCritic()
        self.memory = hybrid_memory or HybridKnowledgeStore()
        self.max_retries_per_task = 3

    async def decompose_goal(self, high_level_goal: str, context: str = "") -> List[SubTaskPlan]:
        """Deconstructs high-level goal into structured sub-tasks with dependency graphs."""
        prompt = (
            f"You are the AETHER Commander Agent directing an autonomous intelligence operation.\n"
            f"HIGH-LEVEL GOAL: {high_level_goal}\n"
            f"TARGET SEED: {self.state.target_seed} (Type: {self.state.target_type.value})\n"
            f"CONTEXT: {context}\n\n"
            f"Decompose this mission into a sequence of atomic subtasks for the following specialist agents:\n"
            f"- 'network_specialist': DNS, Subdomains, BGP/ASN, WHOIS, SSL, Vulnerabilities\n"
            f"- 'vision_specialist': Imagery analysis, Satellite terrain, EXIF GPS coordinates, OCR\n"
            f"- 'audio_specialist': Speech-to-text transcriptions, acoustic intelligence\n"
            f"- 'toolmaker_specialist': Dynamic synthesis of custom Python query tools\n\n"
            f"Define explicit dependencies (e.g. ['task_1']) so independent tasks can run in parallel."
        )

        try:
            decomposition = await model_manager.call_model(
                prompt,
                response_format=PlanTreeDecomposition,
                task_label="Commander Goal Decomposition",
            )
            if isinstance(decomposition, PlanTreeDecomposition) and decomposition.subtasks:
                return decomposition.subtasks
        except Exception as exc:
            logger.warning(f"Fallback heuristic task decomposition: {exc}")

        # Deterministic multi-stage fallback plan
        return [
            SubTaskPlan(
                task_id="task_network_recon",
                specialist="network_specialist",
                instruction=f"Perform perimeter DNS and subdomain discovery for {self.state.target_seed}",
                context_inputs={"domain": self.state.target_seed, "target": self.state.target_seed},
            ),
            SubTaskPlan(
                task_id="task_asn_routing",
                specialist="network_specialist",
                instruction=f"Inspect BGP routing and ASN infrastructure for {self.state.target_seed}",
                context_inputs={"query": self.state.target_seed, "target": self.state.target_seed},
                dependencies=["task_network_recon"],
            ),
        ]

    async def execute_mission(self, high_level_goal: str) -> None:
        """Executes the complete hierarchical mission lifecycle."""
        self.state.status = InvestigationStatus.PLANNING
        logger.info(f"CommanderAgent starting mission: '{high_level_goal}'")

        # Query background context from GraphRAG
        fused_context = self.memory.query_fused_context(
            query=high_level_goal,
            root_entity_id=self.state.target_seed,
        )

        subtasks = await self.decompose_goal(high_level_goal, context=fused_context.synthesized_prompt_context)
        
        completed_tasks: set[str] = set()
        task_queue: Dict[str, SubTaskPlan] = {t.task_id: t for t in subtasks}
        self.state.status = InvestigationStatus.REASONING

        while task_queue and self.state.status in {InvestigationStatus.PLANNING, InvestigationStatus.REASONING, InvestigationStatus.COLLECTING}:
            runnable_tasks = [
                t for t in task_queue.values()
                if all(dep in completed_tasks for dep in t.dependencies)
            ]

            if not runnable_tasks:
                logger.error("Deadlock in task dependencies or remaining tasks blocked.")
                break

            # Execute batch of ready subtasks concurrently
            coroutines = [self._execute_and_verify_task(t) for t in runnable_tasks]
            results = await asyncio.gather(*coroutines, return_exceptions=True)

            for task, res in zip(runnable_tasks, results):
                if isinstance(res, dict) and res.get("success"):
                    completed_tasks.add(task.task_id)
                    del task_queue[task.task_id]
                else:
                    task.retry_count += 1
                    if task.retry_count >= self.max_retries_per_task:
                        logger.error(f"Task [{task.task_id}] failed permanently after {self.max_retries_per_task} attempts.")
                        del task_queue[task.task_id]

        if self.state.status in {InvestigationStatus.PLANNING, InvestigationStatus.REASONING, InvestigationStatus.COLLECTING}:
            self.state.status = InvestigationStatus.COMPLETED
            logger.info("CommanderAgent mission completed successfully.")

    async def _execute_and_verify_task(self, task: SubTaskPlan) -> Dict[str, Any]:
        """Dispatches a task to a specialist, evaluates with Critic, and triggers self-healing if needed."""
        specialist = self.specialists.get(task.specialist)
        if not specialist:
            return {"success": False, "error": f"Unknown specialist: {task.specialist}"}

        logger.info(f"Commander -> [{task.specialist}] for '{task.instruction}'")

        # 1. Execute via Specialist
        try:
            raw_result = await specialist.execute_specialized_task(task.instruction, task.context_inputs)
        except Exception as exc:
            raw_result = {"success": False, "error": str(exc)}

        # 2. If execution encountered a fault, trigger Cognitive Self-Healing
        if not raw_result.get("success") or raw_result.get("error"):
            logger.warning(f"Task [{task.task_id}] encountered fault: {raw_result.get('error')}. Triggering Cognitive Self-Healing.")
            return await self._handle_cognitive_self_healing(
                task,
                raw_result,
                error_msg=str(raw_result.get("error", "Execution failure")),
            )

        # 3. Adversarial Verification via Critic
        verdict_obj = await self.critic.evaluate_finding(
            finding_description=str(raw_result.get("data", "")),
            source_tool=task.specialist,
        )

        verdict_str = (
            verdict_obj.verdict if hasattr(verdict_obj, "verdict")
            else (verdict_obj.get("verdict", "CONFIRMED") if isinstance(verdict_obj, dict) else "CONFIRMED")
        )
        conf_val = (
            verdict_obj.confidence if hasattr(verdict_obj, "confidence")
            else (verdict_obj.get("confidence", 0.85) if isinstance(verdict_obj, dict) else 0.85)
        )

        # 4. Handle Critic Rejection with Cognitive Self-Healing
        if str(verdict_str).upper() == "REJECTED":
            logger.warning(f"Critic rejected result for {task.task_id}. Triggering Cognitive Self-Healing.")
            critic_reason = getattr(verdict_obj, "reasoning", "Evidence refuted by Critic")
            return await self._handle_cognitive_self_healing(task, raw_result, error_msg=critic_reason)

        # 5. Ingest approved finding into GraphRAG & Vector Memory
        finding_id = f"finding_{task.task_id}"
        self.memory.ingest_finding(
            finding_id=finding_id,
            text=f"Task: {task.instruction} | Finding: {raw_result.get('summary', '')}",
        )

        # Update global state
        self.state.add_task_result(
            task_name=task.instruction,
            tool_name=task.specialist,
            result_data=raw_result.get("data", {}),
            confidence=conf_val,
        )

        return {"success": True, "data": raw_result.get("data")}

    async def _handle_cognitive_self_healing(
        self,
        task: SubTaskPlan,
        failed_result: Dict[str, Any],
        error_msg: str,
    ) -> Dict[str, Any]:
        """Runs the self-healing engine to perform RCA, transmute parameters, shift strategy, or synthesize tools."""
        diag, healing_action = await self_healing_engine.formulate_healing_action(
            task_instruction=task.instruction,
            specialist_name=task.specialist,
            error_msg=error_msg,
            failed_output=failed_result.get("data", failed_result),
            context=task.context_inputs,
        )

        target_specialist_name = healing_action.target_tool_name or task.specialist
        specialist = self.specialists.get(target_specialist_name) or self.specialists.get(task.specialist)
        if not specialist:
            return {"success": False, "error": f"Specialist '{target_specialist_name}' unavailable for self-healing"}

        logger.info(f"Self-Healing Strategy [{healing_action.remediation_strategy.value}]: {healing_action.explanation}")

        merged_context = {**task.context_inputs, **healing_action.revised_inputs}
        healing_res = await specialist.execute_specialized_task(
            instruction=healing_action.revised_instruction,
            context=merged_context,
        )

        if healing_res.get("success"):
            # Record successful remedy into Episodic Memory
            target_seed = str(task.context_inputs.get("target") or task.context_inputs.get("domain") or "global")
            self_healing_engine.episodic_memory.record_successful_remediation(
                target=target_seed,
                fault_category=diag.fault_category.value,
                action=healing_action,
            )

            self.state.add_task_result(
                task_name=healing_action.revised_instruction,
                tool_name=target_specialist_name,
                result_data=healing_res.get("data", {}),
                confidence=0.85,
            )
            self.memory.ingest_finding(
                finding_id=f"finding_healed_{task.task_id}",
                text=f"Self-Healed Task: {healing_action.revised_instruction} | Strategy: {healing_action.remediation_strategy.value} | Result: {healing_res.get('summary', '')}",
            )
            return {
                "success": True,
                "data": healing_res.get("data"),
                "healed": True,
                "strategy": healing_action.remediation_strategy.value,
            }

        return healing_res


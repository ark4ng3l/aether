"""
OrchestrationEngine — the central intelligence loop of AETHER.

Cycle: Observation → Planning → Parallel Action → Verification → Synthesis

Features:
  • Structured Task Tracking: records every completed step in ``state.completed_tasks``.
  • Active Task Telemetry: updates ``state.active_task`` in real-time.
  • Context Briefing Injection: LLMs are conditioned on background intelligence notes.
  • EventBus streaming for real-time WebSocket dashboard sync.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from aether.core.state import (
    AgentState,
    Entity,
    EntityType,
    InvestigationStatus,
    RelationshipType,
    TaskStep,
)
from aether.core.logger import logger
from aether.core.events import event_bus
from aether.core.model_manager import model_manager
from aether.config.settings import settings
from aether.reasoning.planner import Planner, PlanAction
from aether.reasoning.hypothesis import HypothesisEngine
from aether.reasoning.critic import RedTeamCritic
from aether.memory.graph_store import GraphStore
from aether.perception.tools.registry import registry


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class OrchestrationEngine:
    """
    Drives the AETHER intelligence cycle.
    Accessible via ``self.state`` for live status and historical data.
    """

    def __init__(
        self,
        target_seed: str,
        project_id: str = "",
        project_name: str = "",
        target_type: EntityType = EntityType.UNKNOWN,
        context_briefing: str = "",
    ):
        inv_id = uuid.uuid4().hex[:12]
        self.state = AgentState(
            investigation_id=inv_id,
            project_id=project_id or inv_id,
            project_name=project_name or f"Investigation {target_seed}",
            target_seed=target_seed,
            target_type=target_type,
            context_briefing=context_briefing,
        )
        self.graph_store = GraphStore()
        self.planner = Planner(self.state)
        self.hypothesis_engine = HypothesisEngine()
        self.critic = RedTeamCritic()
        self.dossier: str = ""

        # Vector store is optional
        self.vector_store = None
        try:
            from aether.memory.vector_store import VectorStore
            self.vector_store = VectorStore()
        except Exception as exc:
            logger.warning(f"Vector store unavailable (non-fatal): {exc}")

        # Ensure tools are registered
        self._ensure_tools()

    # ------------------------------------------------------------------
    # Tool Registration
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_tools():
        """Import the perception tools package which auto-registers everything."""
        try:
            import aether.perception.tools  # noqa: F401
        except Exception as exc:
            logger.warning(f"Some perception tools failed to load: {exc}")

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    async def run_investigation(self):
        inv_id = self.state.investigation_id
        seed = self.state.target_seed

        logger.mission_critical(
            f"Starting investigation #{inv_id} for '{self.state.project_name}' [Seed: {seed}]"
        )
        await self._emit("investigation_started", {
            "seed": seed,
            "project_id": self.state.project_id,
            "project_name": self.state.project_name,
            "context_briefing": self.state.context_briefing,
        })

        self.state.status = InvestigationStatus.PLANNING
        iteration = 0
        max_iter = settings.MAX_SEARCH_DEPTH

        try:
            # ── Add seed as root entity ──
            seed_type = (
                self.state.target_type
                if self.state.target_type != EntityType.UNKNOWN
                else self._guess_entity_type(seed)
            )
            root_entity = Entity(
                id=seed,
                type=seed_type,
                properties={
                    "name": seed,
                    "role": "seed",
                    "briefing": self.state.context_briefing,
                },
            )
            self.state.add_entity(root_entity)
            self.graph_store.add_entity(root_entity)
            await self._emit("entity_discovered", {
                "id": root_entity.id,
                "type": root_entity.type.value,
                "properties": root_entity.properties,
            })

            # ── Main investigation loop ──
            while iteration < max_iter:
                iteration += 1
                await self._emit("status_change", {
                    "status": self.state.status.value,
                    "iteration": iteration,
                    "completed_count": len(self.state.completed_tasks),
                    "pending_tasks": self.state.current_task_stack,
                })

                # 1. PLANNING
                self.state.status = InvestigationStatus.PLANNING
                plan = await self.planner.plan_next_step()

                if plan is None or plan.action == "finish":
                    logger.info("Planner signalled FINISH.")
                    break

                # 2. HYPOTHESIS (Dead-end detected)
                if plan.action == "hypothesis":
                    self.state.status = InvestigationStatus.REASONING
                    await self._emit("status_change", {"status": "reasoning"})

                    evidence = [
                        {"desc": e.id, "type": e.type.value}
                        for e in self.state.discovered_entities
                    ]
                    hypotheses = await self.hypothesis_engine.generate_abductive_hypotheses(
                        evidence=evidence,
                        context_briefing=self.state.context_briefing,
                        target_seed=self.state.target_seed,
                    )
                    logger.info(f"Hypotheses generated: {hypotheses}")
                    self.state.active_hypotheses = hypotheses
                    await self._emit("hypotheses_generated", {
                        "hypotheses": hypotheses,
                        "pending_count": len(self.state.current_task_stack) + len(hypotheses),
                    })

                    # Enqueue hypotheses as search tasks
                    for h in hypotheses:
                        self.state.current_task_stack.append(f"search: {h}")
                    continue

                # 3. ACTION & VERIFICATION
                self.state.status = InvestigationStatus.COLLECTING
                await self._emit("status_change", {"status": "collecting"})
                await self._execute_task_step(plan)

            # ── Synthesis ──
            self.state.status = InvestigationStatus.SYNTHESIZING
            self.state.active_task = None
            await self._emit("status_change", {"status": "synthesizing"})
            self.dossier = await self._synthesize_dossier()
            self.state.dossier = self.dossier
            self.state.status = InvestigationStatus.COMPLETED
            self.state.finished_time = _now_utc()

            await self._emit("investigation_completed", {
                "project_id": self.state.project_id,
                "entities_count": len(self.state.discovered_entities),
                "completed_tasks_count": len(self.state.completed_tasks),
                "dossier_length": len(self.dossier),
            })
            logger.success(
                f"Investigation complete: {len(self.state.discovered_entities)} entities, "
                f"{len(self.state.completed_tasks)} tasks executed."
            )

        except Exception as exc:
            logger.error(f"Orchestration error: {exc}")
            self.state.status = InvestigationStatus.FAILED
            self.state.last_error = str(exc)
            self.state.finished_time = _now_utc()
            await self._emit("error", {"error": str(exc)})

    # ------------------------------------------------------------------
    # Task Step Execution & Tracking
    # ------------------------------------------------------------------

    async def _execute_task_step(self, plan: PlanAction):
        tool_name = plan.tool_name or "web_search"
        start_time = time.time()

        task_step = TaskStep(
            tool_name=tool_name,
            params=plan.params,
            reasoning=plan.reasoning,
            status="running",
        )
        self.state.active_task = task_step

        await self._emit("task_started", {
            "task_id": task_step.id,
            "tool": tool_name,
            "params": plan.params,
            "reasoning": plan.reasoning,
            "pending_count": len(self.state.current_task_stack),
        })

        tool = registry.get_tool(tool_name) or registry.get_tool("web_search")
        if tool is None:
            logger.warning("No tools available in registry.")
            task_step.status = "failed"
            task_step.output_summary = "Tool not found in registry"
            self.state.completed_tasks.append(task_step)
            return

        # Execute tool
        try:
            result = await tool.execute(**plan.params)
        except TypeError:
            query = " ".join(str(v) for v in plan.params.values())
            result = await tool.execute(query=query)
        except Exception as exc:
            result = None
            task_step.status = "failed"
            task_step.output_summary = f"Execution error: {exc}"

        duration = round(time.time() - start_time, 2)
        task_step.duration_seconds = duration

        if result is None or not result.success:
            err = result.error if result else task_step.output_summary
            task_step.status = "failed"
            task_step.output_summary = err
            self.state.completed_tasks.append(task_step)
            self.state.active_task = None
            await self._emit("task_failed", {
                "task_id": task_step.id,
                "tool": tool_name,
                "error": err,
                "duration": duration,
            })
            return

        raw_preview = str(result.data)
        task_step.output_summary = (raw_preview[:250] + "…") if len(raw_preview) > 250 else raw_preview

        # 4. VERIFICATION — Adversarial Critic
        self.state.status = InvestigationStatus.VERIFYING
        await self._emit("status_change", {"status": "verifying"})

        briefing_context = (
            f" Context: {self.state.context_briefing}" if self.state.context_briefing else ""
        )
        verdict = await self.critic.evaluate_finding(
            f"Tool '{tool_name}' returned: {raw_preview[:500]}.{briefing_context}"
        )
        task_step.verdict = verdict.get("verdict", "PLAUSIBLE")
        task_step.confidence = float(verdict.get("confidence", 0.5))

        if task_step.verdict in ("CONFIRMED", "PLAUSIBLE"):
            task_step.status = "completed"
            entity = Entity(
                id=uuid.uuid4().hex[:8],
                type=EntityType.ARTIFACT,
                properties={
                    "source_tool": tool_name,
                    "data": raw_preview[:800],
                    "verdict": task_step.verdict,
                    "confidence": task_step.confidence,
                },
                confidence=task_step.confidence,
            )
            self.state.add_entity(entity)
            self.graph_store.add_entity(entity)
            self.graph_store.add_relationship(
                RelationshipType.ASSOCIATED_WITH,
                source_id=self.state.target_seed,
                target_id=entity.id,
            )

            await self._emit("entity_discovered", {
                "id": entity.id,
                "type": entity.type.value,
                "properties": entity.properties,
            })

            if self.vector_store:
                try:
                    await self.vector_store.add_text(
                        raw_preview[:500],
                        metadata={"entity_id": entity.id, "tool": tool_name},
                    )
                except Exception:
                    pass
        else:
            task_step.status = "rejected"
            logger.info(f"Finding rejected by critic: {verdict.get('reasoning', '')[:100]}")

        self.state.completed_tasks.append(task_step)
        self.state.active_task = None

        await self._emit("task_completed", {
            "task_id": task_step.id,
            "tool": tool_name,
            "status": task_step.status,
            "verdict": task_step.verdict,
            "confidence": task_step.confidence,
            "duration": duration,
            "summary": task_step.output_summary,
            "total_completed": len(self.state.completed_tasks),
            "pending_count": len(self.state.current_task_stack),
        })

    # ------------------------------------------------------------------
    # Dossier Synthesis
    # ------------------------------------------------------------------

    async def _synthesize_dossier(self) -> str:
        """Compile all findings into a structured Markdown dossier conditioned on context."""
        entities_summary = "\n".join(
            f"- [{e.type.value}] {e.id}: {e.properties}"
            for e in self.state.discovered_entities
        )
        edges = self.graph_store.query_all_edges()
        edges_summary = "\n".join(
            f"- {e['source_id']} —[{e['rel_type']}]→ {e['target_id']}"
            for e in edges
        )
        steps_summary = "\n".join(
            f"- {t.tool_name} (Verdict: {t.verdict}, Conf: {t.confidence}): {t.output_summary[:120]}"
            for t in self.state.completed_tasks
        )

        briefing_section = ""
        if self.state.context_briefing:
            briefing_section = f"INVESTIGATION BRIEFING / BACKGROUND:\n{self.state.context_briefing}\n\n"

        prompt = (
            "You are AETHER, a lead intelligence analyst.\n"
            "Compile the following OSINT investigation into an executive Markdown dossier.\n\n"
            f"PROJECT: {self.state.project_name}\n"
            f"TARGET SEED: {self.state.target_seed} ({self.state.target_type.value})\n"
            f"{briefing_section}"
            f"ENTITIES DISCOVERED ({len(self.state.discovered_entities)}):\n{entities_summary}\n\n"
            f"RELATIONSHIPS:\n{edges_summary}\n\n"
            f"INVESTIGATION STEPS:\n{steps_summary}\n\n"
            "Structure the dossier with:\n"
            "# Executive Summary\n"
            "## Key Intelligence Findings & Confidence Assessment\n"
            "## Entity Infrastructure & Social Graph\n"
            "## Attribution & Threat / Risk Assessment\n"
            "## Recommended Next Investigative Steps\n"
        )

        try:
            dossier = await model_manager.call_model(
                prompt,
                model=settings.MODEL_DEEP,
                is_heavy=True,
                temperature=0.3,
            )
            return str(dossier)
        except Exception as exc:
            logger.error(f"Dossier synthesis failed: {exc}")
            return (
                f"# AETHER Dossier — {self.state.project_name}\n\n"
                f"**Target:** `{self.state.target_seed}`\n\n"
                f"**Context Briefing:** {self.state.context_briefing or 'None'}\n\n"
                f"## Entities Discovered ({len(self.state.discovered_entities)})\n"
                f"{entities_summary}\n\n"
                f"## Relationships\n{edges_summary}\n"
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _guess_entity_type(seed: str) -> EntityType:
        if seed.startswith("@"):
            return EntityType.SOCIAL_HANDLE
        if "@" in seed and "." in seed:
            return EntityType.EMAIL
        if seed.replace(".", "").replace(":", "").isdigit():
            return EntityType.IP_ADDRESS
        if "." in seed and " " not in seed:
            return EntityType.DOMAIN
        return EntityType.PERSON

    async def _emit(self, event_type: str, data: dict):
        """Emit event to both project-specific queue and global bus."""
        event = {
            "type": event_type,
            "project_id": self.state.project_id,
            "data": data,
        }
        await event_bus.emit(self.state.project_id, event)
        await event_bus.emit(self.state.investigation_id, event)
        await event_bus.emit_global(event)

"""
OrchestrationEngine — the central intelligence loop of AETHER.

Cycle: Observation → Planning → Parallel Action → Verification → Synthesis

Features:
  • Real-Time Token Streaming: Live thought process broadcasts token-by-token.
  • Structured Task Tracking: records every completed step in ``state.completed_tasks``.
  • Active Task Telemetry: updates ``state.active_task`` in real-time.
  • Context Briefing Injection: LLMs are conditioned on background intelligence notes.
  • Heuristic Entity Harvester: Automatically extracts secondary IPs, domains, handles, and emails from raw tool outputs.
  • Dynamic Task Injection API: Allows manual task/hypothesis injection.
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

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
        self.graph_store = GraphStore(project_id=self.state.project_id)
        self.planner = Planner(self.state)
        self.hypothesis_engine = HypothesisEngine()
        self.critic = RedTeamCritic()
        self.dossier: str = ""
        self._injected_tasks: List[PlanAction] = []

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

    def inject_task(self, tool_name: str, params: Dict[str, Any], reasoning: str = "Manually injected task"):
        """Inject a high-priority task into the active investigation queue."""
        plan = PlanAction(action="execute_tool", tool_name=tool_name, params=params, reasoning=reasoning)
        self._injected_tasks.append(plan)
        self.state.current_task_stack.append(f"manual: {tool_name} ({params})")

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

            # ── Fast-Track Initial Tactical Recon Enqueue ──
            if not self.state.current_task_stack:
                if seed_type == EntityType.DOMAIN:
                    self.state.current_task_stack.extend([
                        f"subdomains: {seed}",
                        f"network: {seed}",
                        f"search: {seed}",
                    ])
                elif seed_type == EntityType.IP_ADDRESS:
                    self.state.current_task_stack.extend([
                        f"geoip: {seed}",
                        f"network: {seed}",
                    ])
                elif seed_type == EntityType.SOCIAL_HANDLE:
                    clean_handle = seed.lstrip("@")
                    self.state.current_task_stack.extend([
                        f"social: {clean_handle}",
                        f"breach: {clean_handle}",
                        f"search: {seed}",
                    ])
                elif seed_type == EntityType.IMAGE:
                    self.state.current_task_stack.append(f"image: {seed}")

            # ── Main investigation loop ──
            while iteration < max_iter:
                iteration += 1
                await self._emit("status_change", {
                    "status": self.state.status.value,
                    "iteration": iteration,
                    "completed_count": len(self.state.completed_tasks),
                    "pending_tasks": self.state.current_task_stack,
                })

                # Check manual injections first
                if self._injected_tasks:
                    plan = self._injected_tasks.pop(0)
                else:
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

        # Execute tool with timeout protection
        try:
            result = await asyncio.wait_for(tool.execute(**plan.params), timeout=25.0)
        except asyncio.TimeoutError:
            result = None
            task_step.status = "failed"
            task_step.output_summary = f"Tool '{tool_name}' timed out after 25s"
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

        # 4. VERIFICATION — Fast & Smart Adversarial Verification
        self.state.status = InvestigationStatus.VERIFYING
        await self._emit("status_change", {"status": "verifying"})

        # Deterministic tools (DNS, IP-API, CT logs, EXIF) return verified technical ground-truth
        DETERMINISTIC_TOOLS = {
            "subdomain_finder", "ip_geolocate", "network_recon",
            "image_osint", "metadata_extractor",
        }

        if tool_name in DETERMINISTIC_TOOLS:
            verdict = {
                "verdict": "CONFIRMED",
                "reasoning": f"Direct technical record verified from {tool_name}",
                "confidence": 0.95,
            }
        else:
            briefing_context = (
                f" Context: {self.state.context_briefing}" if self.state.context_briefing else ""
            )
            verdict = await self.critic.evaluate_finding(
                f"Tool '{tool_name}' returned: {raw_preview[:500]}.{briefing_context}",
                is_heavy=False,
            )

        task_step.verdict = verdict.get("verdict", "PLAUSIBLE")
        task_step.confidence = float(verdict.get("confidence", 0.5))

        if task_step.verdict in ("CONFIRMED", "PLAUSIBLE"):
            task_step.status = "completed"
            main_entity = Entity(
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
            self.state.add_entity(main_entity)
            self.graph_store.add_entity(main_entity)
            self.graph_store.add_relationship(
                RelationshipType.ASSOCIATED_WITH,
                source_id=self.state.target_seed,
                target_id=main_entity.id,
            )

            await self._emit("entity_discovered", {
                "id": main_entity.id,
                "type": main_entity.type.value,
                "properties": main_entity.properties,
            })

            # Automated regex extraction of secondary entities (Emails, IPs, Handles)
            self._harvest_sub_entities(raw_preview, main_entity.id)

            if self.vector_store:
                try:
                    await self.vector_store.add_text(
                        raw_preview[:500],
                        metadata={"entity_id": main_entity.id, "tool": tool_name},
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
    # Automated Sub-Entity Harvester
    # ------------------------------------------------------------------

    def _harvest_sub_entities(self, text: str, parent_id: str):
        """Extract IPs, emails, usernames, and domains from tool output."""
        # 1. Emails
        emails = set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text))
        for email in list(emails)[:4]:
            if not self.state.get_entity(email):
                ent = Entity(id=email, type=EntityType.EMAIL, properties={"discovered_from": parent_id, "name": email})
                self.state.add_entity(ent)
                self.graph_store.add_entity(ent)
                self.graph_store.add_relationship(RelationshipType.ASSOCIATED_WITH, parent_id, email)

        # 2. IPv4 Addresses (Geocoded)
        ips = set(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text))
        for ip in list(ips)[:4]:
            if not ip.startswith(("127.", "0.", "255.", "192.168.", "10.")) and not self.state.get_entity(ip):
                ent = Entity(
                    id=ip,
                    type=EntityType.IP_ADDRESS,
                    properties={
                        "discovered_from": parent_id,
                        "name": ip,
                        "ip": ip,
                    },
                )
                self.state.add_entity(ent)
                self.graph_store.add_entity(ent)
                self.graph_store.add_relationship(RelationshipType.RESOLVES_TO, parent_id, ip)

        # 3. Subdomains & Domains
        domains = set(re.findall(r'\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|co|ir|ru|cn|de|uk|info|biz|me|xyz|top|app|dev)\b', text.lower()))
        for dom in list(domains)[:5]:
            if dom != self.state.target_seed and not self.state.get_entity(dom):
                ent = Entity(id=dom, type=EntityType.DOMAIN, properties={"discovered_from": parent_id, "name": dom})
                self.state.add_entity(ent)
                self.graph_store.add_entity(ent)
                self.graph_store.add_relationship(RelationshipType.SUBDOMAIN_OF if self.state.target_seed in dom else RelationshipType.ASSOCIATED_WITH, self.state.target_seed, dom)

        # 4. Social Handles (@username)
        handles = set(re.findall(r'(?<=[\s,(\'"])@([a-zA-Z0-9_]{3,25})\b', text))
        for h in list(handles)[:3]:
            handle_str = f"@{h}"
            if handle_str != self.state.target_seed and not self.state.get_entity(handle_str):
                ent = Entity(id=handle_str, type=EntityType.SOCIAL_HANDLE, properties={"discovered_from": parent_id, "name": handle_str})
                self.state.add_entity(ent)
                self.graph_store.add_entity(ent)
                self.graph_store.add_relationship(RelationshipType.ASSOCIATED_WITH, parent_id, handle_str)

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
            "You are AETHER, a lead cyber intelligence operations director.\n"
            "Compile the following OSINT investigation into an executive Markdown dossier.\n\n"
            f"PROJECT: {self.state.project_name}\n"
            f"TARGET SEED: {self.state.target_seed} ({self.state.target_type.value})\n"
            f"{briefing_section}"
            f"ENTITIES DISCOVERED ({len(self.state.discovered_entities)}):\n{entities_summary}\n\n"
            f"RELATIONSHIPS:\n{edges_summary}\n\n"
            f"INVESTIGATION STEPS:\n{steps_summary}\n\n"
            "Structure the dossier cleanly with:\n"
            "# 🛡 Executive Intelligence Summary\n"
            "## 🔍 Key Findings & Attribution Confidence\n"
            "## 🌐 Infrastructure, Network & Social Topology\n"
            "## ⚠️ Threat Assessment & Threat Matrix\n"
            "## 📋 Recommended Actionable Steps & Mitigations\n"
        )

        try:
            dossier = await model_manager.call_model(
                prompt,
                model=settings.MODEL_DEEP,
                is_heavy=True,
                temperature=0.3,
                task_label="Dossier Synthesis",
            )
            return str(dossier)
        except Exception as exc:
            logger.error(f"Dossier synthesis failed: {exc}")
            return (
                f"# 🛡 AETHER Intelligence Dossier — {self.state.project_name}\n\n"
                f"**Target:** `{self.state.target_seed}`\n\n"
                f"**Context Briefing:** {self.state.context_briefing or 'None'}\n\n"
                f"## Discovered Entities ({len(self.state.discovered_entities)})\n"
                f"{entities_summary}\n\n"
                f"## Network Topology\n{edges_summary}\n"
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

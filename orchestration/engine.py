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
from aether.memory.entity_resolver import EntityResolver
from aether.perception.tools.registry import registry
from aether.core.resource_arbiter import resource_arbiter
from aether.core.cache import response_cache, circuit_breaker
from aether.core.metrics import metrics_collector

# Per-tool timeout configuration (seconds)
TOOL_TIMEOUTS: dict[str, float] = {
    "web_search": 15.0,
    "subdomain_finder": 20.0,
    "ip_geolocate": 10.0,
    "network_recon": 15.0,
    "social_recon": 20.0,
    "breach_lookup": 25.0,
    "stealth_crawler": 60.0,
    "image_osint": 90.0,
    "vlm_processor": 120.0,
    "metadata_extractor": 10.0,
    "whois_lookup": 15.0,
    "shodan_lookup": 12.0,
    "github_dorker": 20.0,
    "company_recon": 15.0,
    "news_intel": 15.0,
    "threat_intel": 15.0,
}
DEFAULT_TOOL_TIMEOUT = 25.0


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
        self.entity_resolver = EntityResolver(self.graph_store)
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

        metrics_collector.record_investigation_start()
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

            # ── Exhaustive Multi-Tool Initial Fan-Out ──
            initial_tasks = []
            if not self.state.current_task_stack:
                if seed_type == EntityType.DOMAIN:
                    initial_tasks = [
                        f"subdomains: {seed}",
                        f"cert_trans: {seed}",
                        f"passive_dns: {seed}",
                        f"network: {seed}",
                        f"whois: {seed}",
                        f"sec_headers: {seed}",
                        f"threat_rep: {seed}",
                        f"tech: {seed}",
                        f"search: {seed}",
                    ]
                elif seed_type == EntityType.IP_ADDRESS:
                    initial_tasks = [
                        f"geoip: {seed}",
                        f"asn: {seed}",
                        f"ports: {seed}",
                        f"shodan: {seed}",
                        f"threat_rep: {seed}",
                        f"search: {seed}",
                    ]
                elif seed_type == EntityType.SOCIAL_HANDLE:
                    clean_handle = seed.lstrip("@")
                    initial_tasks = [
                        f"deep_social: {clean_handle}",
                        f"social: {clean_handle}",
                        f"github: {clean_handle}",
                        f"breach: {clean_handle}",
                        f"scholarly: {clean_handle}",
                        f"search: {seed}",
                    ]
                elif seed_type == EntityType.EMAIL:
                    initial_tasks = [
                        f"email_oracle: {seed}",
                        f"email_sec: {seed}",
                        f"breach: {seed}",
                        f"search: {seed}",
                    ]
                elif seed_type == EntityType.PHONE:
                    initial_tasks = [
                        f"phone: {seed}",
                        f"search: {seed}",
                    ]
                elif seed_type == EntityType.IMAGE:
                    initial_tasks = [f"image: {seed}"]
                else:
                    # General / Organization / Keyword
                    initial_tasks = [
                        f"company: {seed}",
                        f"scholarly: {seed}",
                        f"news: {seed}",
                        f"search: {seed}",
                    ]

            # Execute initial tasks in PARALLEL for 2-4x speedup
            if initial_tasks:
                self.state.status = InvestigationStatus.COLLECTING
                await self._emit("status_change", {"status": "collecting", "phase": "parallel_recon"})
                logger.info(f"Parallel fan-out: {len(initial_tasks)} initial tasks")
                await self._execute_parallel_tasks(initial_tasks)

            # ── Main investigation loop (0 or negative = Unlimited / Exhaustive Mode) ──
            while (max_iter <= 0 or iteration < max_iter) and self.state.status not in (
                InvestigationStatus.STOPPED,
                InvestigationStatus.FAILED,
            ):
                iteration += 1
                await self._emit("status_change", {
                    "status": self.state.status.value,
                    "iteration": iteration,
                    "is_unlimited": max_iter <= 0,
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

            metrics_collector.record_investigation_complete(True, len(self.state.discovered_entities))
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
            metrics_collector.record_investigation_complete(False, 0)
            await self._emit("error", {"error": str(exc)})

    # ------------------------------------------------------------------
    # Parallel Task Execution (Fan-Out)
    # ------------------------------------------------------------------

    async def _execute_parallel_tasks(self, tasks: list[str]):
        """Execute multiple independent tasks concurrently for initial recon speedup."""
        plan_actions = []
        for task_str in tasks:
            tool_name, params = self.planner._infer_tool(task_str)
            plan_actions.append(PlanAction(
                action="tool_call",
                tool_name=tool_name,
                params=params,
                reasoning=f"Parallel initial recon: {task_str}",
            ))

        if not plan_actions:
            return

        # Execute all tasks concurrently
        async def _safe_execute(plan: PlanAction):
            try:
                await self._execute_task_step(plan)
            except Exception as exc:
                logger.warning(f"Parallel task {plan.tool_name} failed: {exc}")

        await asyncio.gather(*[_safe_execute(p) for p in plan_actions])
        logger.info(f"Parallel fan-out complete: {len(plan_actions)} tasks finished")

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

        # 1. Circuit Breaker check
        is_avail, degrade_reason = circuit_breaker.is_available(tool_name)
        if not is_avail:
            logger.warning(f"Circuit breaker active: {degrade_reason}")
            task_step.status = "failed"
            task_step.output_summary = degrade_reason or f"Tool '{tool_name}' degraded by circuit breaker"
            self.state.completed_tasks.append(task_step)
            self.state.active_task = None
            await self._emit("task_failed", {
                "task_id": task_step.id,
                "tool": tool_name,
                "error": task_step.output_summary,
                "duration": 0.0,
            })
            return

        # 2. Check in-memory response cache
        cached_result = response_cache.get(tool_name, plan.params)
        is_cache_hit = cached_result is not None

        if is_cache_hit:
            result = cached_result
        else:
            # Execute under ResourceArbiter semaphore throttle
            resource_category = "heavy_llm" if "vlm" in tool_name else "network_io"
            timeout = TOOL_TIMEOUTS.get(tool_name, DEFAULT_TOOL_TIMEOUT)

            try:
                async with resource_arbiter.throttle(resource_category):
                    result = await asyncio.wait_for(tool.execute(**plan.params), timeout=timeout)
            except asyncio.TimeoutError:
                result = None
                task_step.status = "failed"
                task_step.output_summary = f"Tool '{tool_name}' timed out after {timeout}s"
            except TypeError:
                query = " ".join(str(v) for v in plan.params.values())
                try:
                    async with resource_arbiter.throttle(resource_category):
                        result = await tool.execute(query=query)
                except Exception as exc:
                    result = None
                    task_step.status = "failed"
                    task_step.output_summary = f"Execution error: {exc}"
            except Exception as exc:
                result = None
                task_step.status = "failed"
                task_step.output_summary = f"Execution error: {exc}"

        duration = round(time.time() - start_time, 2)
        task_step.duration_seconds = duration

        # Record metrics & circuit breaker status
        if result is None or not result.success:
            err = result.error if result else task_step.output_summary
            circuit_breaker.record_failure(tool_name, err)
            metrics_collector.record_tool_execution(tool_name, duration * 1000, False)
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

        # Record success
        circuit_breaker.record_success(tool_name)
        metrics_collector.record_tool_execution(tool_name, duration * 1000, True)
        if not is_cache_hit:
            response_cache.set(tool_name, plan.params, result)

        raw_preview = str(result.data)
        task_step.output_summary = (raw_preview[:250] + "…") if len(raw_preview) > 250 else raw_preview

        # 3. VERIFICATION — Fast & Smart Adversarial Verification
        self.state.status = InvestigationStatus.VERIFYING
        await self._emit("status_change", {"status": "verifying"})

        briefing_context = (
            f" Context: {self.state.context_briefing}" if self.state.context_briefing else ""
        )
        verdict = await self.critic.evaluate_finding(
            f"Tool '{tool_name}' returned: {raw_preview[:500]}.{briefing_context}",
            is_heavy=False,
            source_tool=tool_name,
        )

        task_step.verdict = verdict.get("verdict", "PLAUSIBLE")
        task_step.critic_reasoning = verdict.get("reasoning", "")
        critic_conf = float(verdict.get("confidence", 0.5))

        # Calculate multi-signal confidence with full breakdown
        final_confidence, signals, conf_breakdown = self.entity_resolver.calculate_confidence(
            source_tool=tool_name,
            corroboration_count=1,
            critic_confidence=critic_conf,
        )
        task_step.confidence = final_confidence
        task_step.confidence_breakdown = conf_breakdown

        # Structured terminal logging for analyst review
        verdict_color = "green" if task_step.verdict == "CONFIRMED" else "yellow" if task_step.verdict == "PLAUSIBLE" else "red"
        logger.info(
            f"\n[bold cyan]┌── [CRITIC ADVERSARIAL EVALUATION] ──────────────────────────[/bold cyan]\n"
            f"[cyan]│[/cyan] [bold]Tool:[/bold] {tool_name}\n"
            f"[cyan]│[/cyan] [bold]Verdict:[/bold] [{verdict_color}]{task_step.verdict}[/{verdict_color}] (Critic Conf: {critic_conf:.2f} → Final: [bold]{final_confidence:.2f}[/bold])\n"
            f"[cyan]│[/cyan] [bold]Analysis:[/bold] {task_step.critic_reasoning}\n"
            f"[cyan]│[/cyan] [bold]Breakdown:[/bold] Critic(40%)={critic_conf:.2f} | Format(20%)={conf_breakdown.get('deterministic_format_score',1.0):.2f} | Corroboration(30%)={conf_breakdown.get('corroboration_bonus',0):.2f} | Reliability(10%)={conf_breakdown.get('source_reliability',0.75):.2f}\n"
            f"[bold cyan]└─────────────────────────────────────────────────────────────[/bold cyan]"
        )

        if task_step.verdict in ("CONFIRMED", "PLAUSIBLE"):
            task_step.status = "completed"

            # Generate smart human-friendly label
            tool_title = tool_name.replace("_", " ").title()
            if tool_name == "subdomain_finder":
                sub_count = len(result.data.get("subdomains", [])) if isinstance(result.data, dict) else ""
                human_label = f"Subdomains ({sub_count})" if sub_count else "Subdomains"
            elif tool_name == "ip_geolocate":
                country = result.data.get("country", "") if isinstance(result.data, dict) else ""
                human_label = f"GeoIP: {country}" if country else "IP Geolocation"
            elif tool_name == "network_recon":
                human_label = "DNS & Network"
            elif tool_name == "social_recon":
                handle = result.data.get("username", "") if isinstance(result.data, dict) else ""
                human_label = f"Social: @{handle}" if handle else "Social Profiles"
            elif tool_name == "image_osint":
                human_label = "Image Forensics"
            elif tool_name == "breach_lookup":
                human_label = "Breach Intel"
            elif tool_name == "company_recon":
                human_label = "Corporate Registry"
            elif tool_name == "news_intel":
                human_label = "News & Media"
            elif tool_name == "threat_intel":
                human_label = "Threat Reputation"
            elif tool_name == "web_search":
                human_label = "Web Intel"
            else:
                human_label = tool_title

            structured_data = result.data if isinstance(result.data, (dict, list)) else {"summary": raw_preview[:800]}

            main_entity = Entity(
                id=f"{tool_name}_{uuid.uuid4().hex[:6]}",
                type=EntityType.ARTIFACT,
                confidence=task_step.confidence,
                confidence_signals=signals,
                properties={
                    "name": human_label,
                    "label": human_label,
                    "source_tool": tool_name,
                    "data": structured_data,
                    "raw_preview": raw_preview[:800],
                    "verdict": task_step.verdict,
                    "confidence": task_step.confidence,
                    "confidence_breakdown": conf_breakdown,
                    "provenance": {
                        "tool": tool_name,
                        "timestamp": _now_utc().isoformat(),
                        "params": plan.params,
                        "duration_s": duration,
                        "cache_hit": is_cache_hit,
                    },
                },
            )
            self.state.add_entity(main_entity)
            self.graph_store.add_entity(main_entity)
            self.graph_store.add_relationship(
                RelationshipType.ASSOCIATED_WITH,
                source_id=self.state.target_seed,
                target_id=main_entity.id,
            )
            task_step.produced_entity_ids.append(main_entity.id)

            await self._emit("entity_discovered", {
                "id": main_entity.id,
                "type": main_entity.type.value,
                "properties": main_entity.properties,
                "confidence": main_entity.confidence,
                "confidence_signals": [s.model_dump() for s in main_entity.confidence_signals],
            })

            # Automated regex extraction of secondary entities (Emails, IPs, Handles)
            self._harvest_sub_entities(raw_preview, main_entity.id, task_step)

            if self.vector_store:
                try:
                    await self.vector_store.add_text(
                        raw_preview[:500],
                        metadata={
                            "entity_id": main_entity.id,
                            "tool": tool_name,
                            "project_id": self.state.project_id,
                        },
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
            "critic_reasoning": task_step.critic_reasoning,
            "confidence_breakdown": task_step.confidence_breakdown,
            "duration": duration,
            "summary": task_step.output_summary,
            "produced_entity_ids": task_step.produced_entity_ids,
            "total_completed": len(self.state.completed_tasks),
            "pending_count": len(self.state.current_task_stack),
        })

    # ------------------------------------------------------------------
    # Automated Sub-Entity Harvester
    # ------------------------------------------------------------------

    def _harvest_sub_entities(self, text: str, parent_id: str, task_step: Optional[TaskStep] = None):
        """Extract all IPs, emails, usernames, domains, CVEs, and hashes from tool output without artificial limits."""
        # 1. All Emails
        emails = set(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text))
        for email in emails:
            self._add_sub_entity(email, EntityType.EMAIL, parent_id, RelationshipType.ASSOCIATED_WITH, task_step)

        # 2. All IPv4 Addresses (filter private/loopback)
        ips = set(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text))
        for ip in ips:
            if not ip.startswith(("127.", "0.", "255.", "192.168.", "10.", "172.")):
                self._add_sub_entity(ip, EntityType.IP_ADDRESS, parent_id, RelationshipType.RESOLVES_TO, task_step)

        # 3. All Subdomains & Domains
        domains = set(re.findall(
            r'\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|co|ir|ru|cn|de|uk|info|biz|me|xyz|top|app|dev|gov|mil|edu|onion|tech|cloud|security)\b',
            text.lower()
        ))
        for dom in domains:
            if dom != self.state.target_seed:
                rel = RelationshipType.SUBDOMAIN_OF if self.state.target_seed in dom else RelationshipType.ASSOCIATED_WITH
                self._add_sub_entity(dom, EntityType.DOMAIN, self.state.target_seed, rel, task_step)

        # 4. All Social Handles (@username)
        handles = set(re.findall(r'(?<=[\s,(\'")])@([a-zA-Z0-9_]{3,25})\b', text))
        for h in handles:
            handle_str = f"@{h}"
            if handle_str != self.state.target_seed:
                self._add_sub_entity(handle_str, EntityType.SOCIAL_HANDLE, parent_id, RelationshipType.ASSOCIATED_WITH, task_step)

        # 5. All CVE Identifiers (CVE-YYYY-NNNNN)
        cves = set(re.findall(r'\bCVE-\d{4}-\d{4,7}\b', text, re.IGNORECASE))
        for cve in cves:
            self._add_sub_entity(cve.upper(), EntityType.CVE, parent_id, RelationshipType.ASSOCIATED_WITH, task_step)

        # 6. Cryptocurrency Wallet Addresses (ETH, BTC, TRON)
        eth_addrs = set(re.findall(r'\b0x[a-fA-F0-9]{40}\b', text))
        for eth in eth_addrs:
            self._add_sub_entity(eth, EntityType.CRYPTO_WALLET, parent_id, RelationshipType.ASSOCIATED_WITH, task_step)

        btc_addrs = set(re.findall(r'\b(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{38,59})\b', text))
        for btc in btc_addrs:
            if not btc.startswith("127."):
                self._add_sub_entity(btc, EntityType.CRYPTO_WALLET, parent_id, RelationshipType.ASSOCIATED_WITH, task_step)

        trx_addrs = set(re.findall(r'\bT[A-Za-z1-9]{33}\b', text))
        for trx in trx_addrs:
            self._add_sub_entity(trx, EntityType.CRYPTO_WALLET, parent_id, RelationshipType.ASSOCIATED_WITH, task_step)

    def _add_sub_entity(
        self, entity_id: str, entity_type: EntityType,
        parent_id: str, rel_type: RelationshipType,
        task_step: Optional[TaskStep] = None,
    ):
        """Add a sub-entity with deduplication via EntityResolver and link to task provenance."""
        if self.state.get_entity(entity_id):
            return  # Already known

        new_entity = Entity(
            id=entity_id,
            type=entity_type,
            properties={"discovered_from": parent_id, "name": entity_id},
        )

        # Try to resolve against existing entities to avoid duplicates
        try:
            existing = self.entity_resolver.resolve(new_entity)
            if existing:
                # Merge: add relationship to existing entity instead of creating duplicate
                self.graph_store.add_relationship(rel_type, parent_id, existing.id)
                return
        except Exception:
            pass  # Resolver failure is non-fatal

        self.state.add_entity(new_entity)
        self.graph_store.add_entity(new_entity)
        self.graph_store.add_relationship(rel_type, parent_id, entity_id)

        if task_step:
            task_step.produced_entity_ids.append(entity_id)

        # ── Recursive Pivot: Auto-enqueue deep follow-up probes ──
        if len(self.state.current_task_stack) < 35:
            if entity_type == EntityType.DOMAIN:
                self.state.current_task_stack.append(f"passive_dns: {entity_id}")
                self.state.current_task_stack.append(f"sec_headers: {entity_id}")
            elif entity_type == EntityType.IP_ADDRESS:
                self.state.current_task_stack.append(f"geoip: {entity_id}")
                self.state.current_task_stack.append(f"asn: {entity_id}")
            elif entity_type == EntityType.EMAIL:
                self.state.current_task_stack.append(f"email_oracle: {entity_id}")
                self.state.current_task_stack.append(f"email_sec: {entity_id}")
            elif entity_type == EntityType.SOCIAL_HANDLE:
                self.state.current_task_stack.append(f"deep_social: {entity_id.lstrip('@')}")
            elif entity_type == EntityType.CVE:
                self.state.current_task_stack.append(f"threat_rep: {entity_id}")


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

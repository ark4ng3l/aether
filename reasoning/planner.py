"""
Planner — Graph-of-Thoughts task planner with entropy-based dead-end detection.

Conditioned on target seed, target type, and user-provided context briefing.
Outputs structured ``PlanAction`` objects that the engine can dispatch.
"""

from __future__ import annotations

import json
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field

from aether.core.state import AgentState, InvestigationStatus
from aether.core.model_manager import model_manager
from aether.core.logger import logger
from aether.config.settings import settings


# ------------------------------------------------------------------
# Structured action schema
# ------------------------------------------------------------------

class PlanAction(BaseModel):
    """Atomic action returned by the planner to the orchestration engine."""
    action: str = Field(
        ...,
        description="One of: tool_call, hypothesis, finish",
    )
    tool_name: Optional[str] = Field(
        None,
        description="Registry tool name when action == 'tool_call'",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments forwarded to the tool",
    )
    reasoning: str = Field("", description="Short justification for this step")


# ------------------------------------------------------------------
# Planner
# ------------------------------------------------------------------

class Planner:
    """
    Manages the investigation trajectory using a Graph-of-Thoughts approach.
    Integrates user-provided intelligence context to tailor OSINT strategies.
    """

    def __init__(self, state: AgentState):
        self.state = state
        self._previous_entity_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def plan_next_step(self) -> Optional[PlanAction]:
        """Analyse current state and return the next ``PlanAction``."""
        if self.state.status in (
            InvestigationStatus.COMPLETED,
            InvestigationStatus.FAILED,
            InvestigationStatus.STOPPED,
        ):
            return None

        # ── Fast path: consume queued tasks first ──
        if self.state.current_task_stack:
            task = self.state.current_task_stack.pop(0)
            tool, params = self._infer_tool(task)
            return PlanAction(
                action="tool_call",
                tool_name=tool,
                params=params,
                reasoning=f"Executing queued task: {task}",
            )

        # ── Entropy check: dead-end detection ──
        current_count = len(self.state.discovered_entities)
        gain = current_count - self._previous_entity_count
        self._previous_entity_count = current_count

        if current_count > 0 and gain == 0:
            logger.warning("Low information gain — switching to Hypothesis Mode.")
            return PlanAction(action="hypothesis", reasoning="Dead-end detected")

        # ── Ask the LLM for the next step ──
        available_tools = [
            "image_osint", "subdomain_finder", "ip_geolocate", "breach_lookup",
            "web_search", "social_recon", "network_recon",
            "stealth_crawler", "vlm_processor", "metadata_extractor",
            "whois_lookup", "shodan_lookup", "github_dorker",
        ]

        context_section = ""
        if self.state.context_briefing:
            context_section = f"\nTARGET BRIEFING / CONTEXT:\n{self.state.context_briefing}\n"

        # Build completed-task summary so the LLM knows what was already done
        completed_summary = ""
        if self.state.completed_tasks:
            recent = self.state.completed_tasks[-8:]  # Last 8 tasks
            lines = []
            for t in recent:
                verdict_str = f"[{t.verdict}]" if t.verdict else "[N/A]"
                lines.append(
                    f"  • {t.tool_name} {verdict_str} (conf={t.confidence:.0%}): "
                    f"{t.output_summary[:120]}"
                )
            completed_summary = (
                f"\nCOMPLETED TASKS (last {len(recent)}):\n"
                + "\n".join(lines) + "\n"
            )

        # Active hypotheses
        hypo_section = ""
        if self.state.active_hypotheses:
            hypo_section = (
                f"\nACTIVE HYPOTHESES:\n"
                + "\n".join(f"  • {h}" for h in self.state.active_hypotheses[:5])
                + "\n"
            )

        prompt = (
            "You are AETHER's autonomous task planner for an OSINT investigation.\n\n"
            f"PROJECT: {self.state.project_name or self.state.target_seed}\n"
            f"TARGET SEED: {self.state.target_seed} (Type: {self.state.target_type.value})\n"
            f"{context_section}"
            f"STATUS: {self.state.status.value}\n"
            f"COMPLETED STEPS: {len(self.state.completed_tasks)}\n"
            f"{completed_summary}"
            f"{hypo_section}"
            f"DISCOVERED ENTITIES ({current_count}): "
            f"{[e.id for e in self.state.discovered_entities[:15]]}\n\n"
            f"AVAILABLE TOOLS: {available_tools}\n\n"
            "RULES:\n"
            "- Do NOT re-run a tool that already completed with the same parameters.\n"
            "- Prioritize tools that follow up on discovered entities (e.g., GeoIP on new IPs, social on new handles).\n"
            "- If sufficient intelligence has been gathered, respond with 'finish'.\n\n"
            "Respond ONLY with a JSON object:\n"
            '{"action":"tool_call","tool_name":"<tool>","params":{"query":"<value>"},"reasoning":"..."}\n'
            'OR {"action":"finish","reasoning":"..."}\n'
        )

        try:
            result = await model_manager.call_model(
                prompt, response_format=PlanAction, temperature=settings.PLANNER_TEMPERATURE,
            )
            if isinstance(result, PlanAction):
                return result
            if isinstance(result, str):
                return self._parse_raw_plan(result)
        except Exception as exc:
            logger.warning(f"Planner LLM call failed: {exc} — using heuristic plan")

        # ── Deterministic Heuristic Fallback based on Target Type ──
        if self.state.target_type == EntityType.IMAGE:
            return PlanAction(
                action="tool_call",
                tool_name="image_osint",
                params={"image_path": self.state.target_seed},
                reasoning="Primary Image OSINT: EXIF, GPS, Perceptual Hashes, Reverse Search & Vision OCR",
            )
        elif self.state.target_type == EntityType.DOMAIN:
            return PlanAction(
                action="tool_call",
                tool_name="subdomain_finder",
                params={"domain": self.state.target_seed},
                reasoning="Domain Target: Enumerate subdomains via Certificate Transparency",
            )
        elif self.state.target_type == EntityType.IP_ADDRESS:
            return PlanAction(
                action="tool_call",
                tool_name="ip_geolocate",
                params={"ip": self.state.target_seed},
                reasoning="IP Target: Geolocate country, city, ISP, and ASN",
            )
        elif self.state.target_type == EntityType.SOCIAL_HANDLE:
            return PlanAction(
                action="tool_call",
                tool_name="social_recon",
                params={"username": self.state.target_seed},
                reasoning="Social Target: Multi-platform profile verification",
            )
        else:
            return PlanAction(
                action="tool_call",
                tool_name="web_search",
                params={"query": f"OSINT {self.state.target_seed}"},
                reasoning="Fallback: generic search",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_tool(task: str) -> tuple[str, dict]:
        """Map a free-text task to a (tool_name, params) tuple."""
        lower = task.lower()
        val = task.split(":", 1)[-1].strip() if ":" in task else task.strip()
        if "image" in lower or "photo" in lower or "exif" in lower or lower.endswith((".jpg", ".png", ".webp", ".jpeg")):
            return "image_osint", {"image_path": val}
        if "subdomain" in lower or "crt" in lower:
            return "subdomain_finder", {"domain": val}
        if "geo" in lower or "geoip" in lower or lower.startswith("ip:"):
            return "ip_geolocate", {"ip": val}
        if "breach" in lower or "leak" in lower:
            return "breach_lookup", {"query": val}
        if "social" in lower or "username" in lower or "handle" in lower:
            return "social_recon", {"username": val}
        if "whois" in lower or "registrar" in lower or "registration" in lower:
            return "whois_lookup", {"domain": val}
        if "shodan" in lower or "port" in lower or "cve" in lower or "vuln" in lower:
            return "shodan_lookup", {"ip": val}
        if "github" in lower or "secret" in lower or "dork" in lower or "leaked" in lower:
            return "github_dorker", {"query": val}
        if "dns" in lower or "domain" in lower or "network" in lower:
            return "network_recon", {"domain": val}
        if "crawl" in lower or "http" in lower:
            return "stealth_crawler", {"url": val}
        # Default
        return "web_search", {"query": val}

    @staticmethod
    def _parse_raw_plan(text: str) -> PlanAction:
        """Best-effort extraction of a PlanAction from free-form LLM text."""
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            data = json.loads(text[start:end])
            return PlanAction.model_validate(data)
        except Exception:
            return PlanAction(
                action="tool_call",
                tool_name="web_search",
                params={"query": text[:200]},
                reasoning="Parsed from raw LLM output",
            )

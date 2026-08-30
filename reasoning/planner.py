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

        # ── Entropy check: progressive stagnation detection (require 3 consecutive zero-gain steps) ──
        current_count = len(self.state.discovered_entities)
        gain = current_count - self._previous_entity_count
        self._previous_entity_count = current_count

        if not hasattr(self, "_stagnant_steps"):
            self._stagnant_steps = 0

        if gain > 0:
            self._stagnant_steps = 0
        else:
            self._stagnant_steps += 1

        if current_count > 0 and self._stagnant_steps >= 3 and not self.state.current_task_stack:
            logger.warning("Consecutive low information gain — triggering Hypothesis Abductive Engine.")
            self._stagnant_steps = 0
            return PlanAction(action="hypothesis", reasoning="Consecutive zero-gain steps detected")

        # ── Ask the LLM for the next step across all 34 tools ──
        available_tools = [
            # Infrastructure & Network
            "subdomain_finder", "network_recon", "ip_geolocate", "asn_lookup",
            "ssl_cert_inspector", "passive_dns", "cert_transparency", "port_prober",
            "security_headers_auditor", "api_schema_inspector", "whois_lookup", "shodan_lookup",
            # Threat & Leaks
            "breach_lookup", "threat_intel", "threat_reputation", "cloud_bucket_recon",
            "typosquat_recon", "favicon_fingerprint", "tech_stack_fingerprint",
            # Search & Media
            "web_search", "news_intel", "wayback_lookup", "robots_sitemap_recon",
            # Persona & Identity OSINT
            "email_oracle", "phone_intel", "deep_social_matrix", "scholarly_intel",
            "social_recon", "github_dorker", "company_recon", "email_security_auditor",
            # Visual Forensics & Steganography
            "image_osint", "vlm_processor", "metadata_extractor", "stealth_crawler",
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
            "- Deeply investigate without stopping early. Exhaustively pivot on newly discovered subdomains, IPs, emails, handles, and technologies.\n"
            "- Do NOT re-run a tool that already completed with the same parameters.\n"
            "- Only respond with 'finish' if all 34 angles and sub-entities are genuinely exhausted.\n\n"
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
                tool_name="deep_social_matrix",
                params={"handle": self.state.target_seed},
                reasoning="Social Target: 50+ platform digital presence matrix",
            )
        elif self.state.target_type == EntityType.EMAIL:
            return PlanAction(
                action="tool_call",
                tool_name="email_oracle",
                params={"email": self.state.target_seed},
                reasoning="Email Target: Online service oracle & avatar reconnaissance",
            )
        elif self.state.target_type == EntityType.PHONE:
            return PlanAction(
                action="tool_call",
                tool_name="phone_intel",
                params={"phone": self.state.target_seed},
                reasoning="Phone Target: International carrier, line type, and VoIP discovery",
            )
        else:
            return PlanAction(
                action="tool_call",
                tool_name="web_search",
                params={"query": f"OSINT {self.state.target_seed}"},
                reasoning="Fallback: multi-engine web search",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_tool(task: str) -> tuple[str, dict]:
        """Map a free-text task to a (tool_name, params) tuple across all 34 tools."""
        lower = task.lower()
        val = task.split(":", 1)[-1].strip() if ":" in task else task.strip()

        # Image
        if "image" in lower or "photo" in lower or "exif" in lower or lower.endswith((".jpg", ".png", ".webp", ".jpeg")):
            return "image_osint", {"image_path": val}

        # Persona & Identity OSINT
        if "email_oracle" in lower or ("oracle" in lower and "@" in lower):
            return "email_oracle", {"email": val}
        if "email_sec" in lower or "spf" in lower or "dmarc" in lower or "dkim" in lower:
            return "email_security_auditor", {"domain_or_email": val}
        if "phone" in lower or "tel" in lower or lower.startswith("+") or lower.startswith("phone:"):
            return "phone_intel", {"phone": val}
        if "deep_social" in lower or "matrix" in lower:
            return "deep_social_matrix", {"handle": val}
        if "scholarly" in lower or "paper" in lower or "author" in lower or "crossref" in lower:
            return "scholarly_intel", {"author_name": val}

        # Infrastructure & Network
        if "cert_trans" in lower or "ct_logs" in lower or "crt.sh" in lower:
            return "cert_transparency", {"domain": val}
        if "passive_dns" in lower or "pdns" in lower or "otx" in lower:
            return "passive_dns", {"domain": val}
        if "port" in lower or "probe" in lower or "banner" in lower or "open_ports" in lower:
            return "port_prober", {"host": val}
        if "sec_headers" in lower or "csp" in lower or "hsts" in lower or "cors" in lower or "headers" in lower:
            return "security_headers_auditor", {"domain_or_url": val}
        if "api_schema" in lower or "swagger" in lower or "openapi" in lower or "graphql" in lower:
            return "api_schema_inspector", {"domain_or_url": val}
        if "threat_rep" in lower or "urlhaus" in lower or "threatfox" in lower or "feodo" in lower:
            return "threat_reputation", {"target": val}

        # Subdomains & DNS
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
        if "shodan" in lower or "cve" in lower or "vuln" in lower:
            return "shodan_lookup", {"ip": val}
        if "github" in lower or "secret" in lower or "dork" in lower or "leaked" in lower:
            return "github_dorker", {"query": val}
        if "company" in lower or "corp" in lower or "incorporation" in lower or "registry" in lower:
            return "company_recon", {"company_name": val}
        if "news" in lower or "article" in lower or "headline" in lower or "rss" in lower:
            return "news_intel", {"query": val}
        if "threat" in lower or "malware" in lower or "reputation" in lower or "abuse" in lower:
            return "threat_intel", {"target": val}
        if "wayback" in lower or "archive" in lower or "snapshot" in lower:
            return "wayback_lookup", {"domain": val}
        if "favicon" in lower or "mmh3" in lower:
            return "favicon_fingerprint", {"domain": val}
        if "tech" in lower or "stack" in lower or "wappalyzer" in lower:
            return "tech_stack_fingerprint", {"domain": val}
        if "typosquat" in lower or "squat" in lower or "permutation" in lower:
            return "typosquat_recon", {"domain": val}
        if "asn" in lower or "bgp" in lower or "routing" in lower:
            return "asn_lookup", {"query": val}
        if "ssl" in lower or "cert" in lower or "x509" in lower or "tls" in lower:
            return "ssl_cert_inspector", {"domain": val}
        if "bucket" in lower or "s3" in lower or "gcs" in lower or "blob" in lower:
            return "cloud_bucket_recon", {"target": val}
        if "robot" in lower or "sitemap" in lower:
            return "robots_sitemap_recon", {"domain": val}
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

"""
Autonomous Cognitive Self-Healing & Resilience Engine for AETHER v4.0.
Provides Root Cause Analysis (RCA), real-time fault classification, parameter transmutation,
passive strategy shifting, episodic failure memory, and autonomous error remediation.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from aether.core.logger import logger
from aether.core.model_manager import model_manager


class FaultCategory(str, enum.Enum):
    """Taxonomy of runtime faults and intelligence collection barriers."""
    INPUT_FORMAT_ERROR = "input_format_error"
    RATE_LIMITED_OR_BLOCKED = "rate_limited_or_blocked"
    TARGET_UNREACHABLE = "target_unreachable"
    TOOL_DEFICIENCY = "tool_deficiency"
    CRITIC_REJECTION = "critic_rejection"
    UNKNOWN_TRANSIENT = "unknown_transient"


class RemediationStrategy(str, enum.Enum):
    """Actionable remediation strategies synthesized by the self-healing engine."""
    MUTATE_PARAMS = "mutate_params"
    SHIFT_TO_PASSIVE_MIRROR = "shift_to_passive_mirror"
    SYNTHESIZE_TOOL = "synthesize_tool"
    PRUNE_AND_REROUTE = "prune_and_reroute"
    EXPONENTIAL_BACKOFF = "exponential_backoff"


class FaultDiagnosis(BaseModel):
    """Result of Cognitive Root Cause Analysis."""
    fault_category: FaultCategory = Field(..., description="High-level category of the fault")
    root_cause_explanation: str = Field(..., description="Technical explanation of why the operation failed")
    suggested_strategy: RemediationStrategy = Field(..., description="Recommended remediation strategy")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Confidence in this diagnosis")


class HealingAction(BaseModel):
    """Executable plan to remediate a diagnosed fault."""
    remediation_strategy: RemediationStrategy = Field(..., description="Chosen strategy")
    revised_instruction: str = Field(..., description="Updated subtask instruction")
    revised_inputs: Dict[str, Any] = Field(default_factory=dict, description="Transmuted / corrected input parameters")
    synthesized_code_required: bool = Field(default=False, description="Whether dynamic tool synthesis is required")
    target_tool_name: Optional[str] = Field(default=None, description="Alternative tool or specialist to invoke")
    explanation: str = Field(default="", description="Operator-facing explanation of the healing action taken")


class CognitiveFaultClassifier:
    """Classifies runtime errors and performs Root Cause Analysis (RCA)."""

    @staticmethod
    def classify_heuristically(error_str: str, raw_output: Any) -> FaultDiagnosis:
        """Deterministic heuristic classifier for instant offline RCA."""
        err_lower = str(error_str).lower()
        out_str = str(raw_output).lower()
        combined = f"{err_lower} {out_str}"

        # 1. Rate-limiting & WAF blocks
        if any(term in combined for term in ["429", "too many requests", "rate limit", "403", "forbidden", "cloudflare", "blocked by cloudflare", "waf", "captcha", "access denied"]):
            return FaultDiagnosis(
                fault_category=FaultCategory.RATE_LIMITED_OR_BLOCKED,
                root_cause_explanation="Target server or upstream API triggered rate-limiting, Cloudflare challenge, or WAF block.",
                suggested_strategy=RemediationStrategy.SHIFT_TO_PASSIVE_MIRROR,
                confidence=0.95,
            )

        # 2. Input / Formatting errors
        if any(term in combined for term in ["invalid domain", "invalid ip", "missing parameter", "valueerror", "invalid format", "schema mismatch", "failed to parse", "bad url", "unknown host"]):
            return FaultDiagnosis(
                fault_category=FaultCategory.INPUT_FORMAT_ERROR,
                root_cause_explanation="Input parameter formatting mismatch (e.g. protocol in domain, unstripped whitespace, or wrong data type).",
                suggested_strategy=RemediationStrategy.MUTATE_PARAMS,
                confidence=0.92,
            )

        # 3. Target unreachable / Network timeouts
        if any(term in combined for term in ["timeout", "timed out", "connection refused", "network is unreachable", "connection error", "host not found", "getaddrinfo failed"]):
            return FaultDiagnosis(
                fault_category=FaultCategory.TARGET_UNREACHABLE,
                root_cause_explanation="Host is offline, DNS query failed to resolve, or port connection timed out.",
                suggested_strategy=RemediationStrategy.SHIFT_TO_PASSIVE_MIRROR,
                confidence=0.88,
            )

        # 4. Tool deficiency / Missing parser
        if any(term in combined for term in ["no tool found", "not implemented", "unsupported format", "unknown specialist", "keyerror", "attributeerror"]):
            return FaultDiagnosis(
                fault_category=FaultCategory.TOOL_DEFICIENCY,
                root_cause_explanation="Existing tool ecosystem lacks a specialized parser or capability for this target response.",
                suggested_strategy=RemediationStrategy.SYNTHESIZE_TOOL,
                confidence=0.85,
            )

        # 5. Default fallback
        return FaultDiagnosis(
            fault_category=FaultCategory.UNKNOWN_TRANSIENT,
            root_cause_explanation=f"Transient execution error: {error_str[:200]}",
            suggested_strategy=RemediationStrategy.EXPONENTIAL_BACKOFF,
            confidence=0.60,
        )

    async def diagnose_fault(
        self,
        task_instruction: str,
        error_msg: str,
        failed_output: Any,
        context: Dict[str, Any],
    ) -> FaultDiagnosis:
        """Performs deep LLM-backed Root Cause Analysis with heuristic fallback."""
        heuristic = self.classify_heuristically(error_msg, failed_output)
        if heuristic.confidence >= 0.90:
            return heuristic

        prompt = (
            f"You are the AETHER Cognitive Fault Diagnosis and Root Cause Analysis Engine.\n"
            f"A subtask execution has failed or encountered a defensive barrier.\n\n"
            f"SUBTASK INSTRUCTION: {task_instruction}\n"
            f"CONTEXT INPUTS: {json.dumps(context, default=str)}\n"
            f"ERROR MESSAGE / TRACEBACK: {error_msg}\n"
            f"FAILED OUTPUT SAMPLE: {str(failed_output)[:500]}\n\n"
            f"Analyze the root cause and output a structured FaultDiagnosis.\n"
            f"Choose the most accurate fault_category from: input_format_error, rate_limited_or_blocked, "
            f"target_unreachable, tool_deficiency, critic_rejection, unknown_transient.\n"
            f"Choose suggested_strategy from: mutate_params, shift_to_passive_mirror, synthesize_tool, prune_and_reroute, exponential_backoff."
        )

        try:
            diag = await model_manager.call_model(
                prompt,
                response_format=FaultDiagnosis,
                task_label="Cognitive Fault Diagnosis",
            )
            if isinstance(diag, FaultDiagnosis):
                return diag
        except Exception as exc:
            logger.warning(f"Cognitive fault diagnosis LLM fallback: {exc}")

        return heuristic


class EpisodicFailureMemory:
    """
    Episodic memory retaining known failure patterns and proven remedies.
    Enables pre-emptive self-healing on subsequent tasks.
    """

    def __init__(self):
        self._memory: Dict[str, HealingAction] = {}

    @staticmethod
    def _compute_pattern_key(target: str, fault_category: str) -> str:
        raw = f"{target.strip().lower()}::{fault_category.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def record_successful_remediation(self, target: str, fault_category: str, action: HealingAction) -> None:
        """Stores a successful healing action for this target and fault category."""
        key = self._compute_pattern_key(target, fault_category)
        self._memory[key] = action
        logger.info(f"EpisodicFailureMemory: Stored proven remedy for target '{target}' [{fault_category}]")

    def get_proven_remediation(self, target: str, fault_category: str) -> Optional[HealingAction]:
        """Retrieves a previously successful healing action if one exists."""
        key = self._compute_pattern_key(target, fault_category)
        return self._memory.get(key)

    def clear(self) -> None:
        """Clears episodic memory cache."""
        self._memory.clear()


class SelfHealingEngine:
    """
    Core engine orchestrating Root Cause Analysis, parameter transmutation,
    strategy shifting, and dynamic tool synthesis to heal failed tasks.
    """

    def __init__(self, episodic_memory: Optional[EpisodicFailureMemory] = None):
        self.classifier = CognitiveFaultClassifier()
        self.episodic_memory = episodic_memory or EpisodicFailureMemory()

    @staticmethod
    def transmute_parameters(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cognitive parameter normalizer: automatically cleans domains, IPs, URLs, and queries.
        """
        mutated = dict(context)

        # 1. Clean domain / target parameters
        for key in ["domain", "target", "query", "url", "host", "ip"]:
            val = mutated.get(key)
            if not isinstance(val, str):
                continue
            val = val.strip()

            # Extract pure domain from full URL if tool expects domain
            if key in ["domain", "host"] and (val.startswith("http://") or val.startswith("https://")):
                parsed = urlparse(val)
                extracted_domain = parsed.hostname or parsed.path.split("/")[0]
                mutated[key] = extracted_domain
                mutated["domain"] = extracted_domain

            # If tool expects URL and got bare domain, add https://
            elif key == "url" and not (val.startswith("http://") or val.startswith("https://")):
                mutated[key] = f"https://{val}"

            # Strip port or trailing paths from domain
            elif key == "domain" and ":" in val and not val.startswith("http"):
                mutated[key] = val.split(":")[0]

            # Strip CIDR subnet mask if single IP expected
            elif key == "ip" and "/" in val:
                mutated[key] = val.split("/")[0]

        return mutated

    async def formulate_healing_action(
        self,
        task_instruction: str,
        specialist_name: str,
        error_msg: str,
        failed_output: Any,
        context: Dict[str, Any],
    ) -> Tuple[FaultDiagnosis, HealingAction]:
        """
        Diagnoses a failure and generates an actionable healing plan.
        """
        # 1. Check episodic memory for pre-existing successful pattern
        target_seed = str(context.get("target") or context.get("domain") or context.get("ip") or "global")
        heuristic_diag = CognitiveFaultClassifier.classify_heuristically(error_msg, failed_output)
        
        cached_action = self.episodic_memory.get_proven_remediation(target_seed, heuristic_diag.fault_category.value)
        if cached_action:
            logger.info(f"SelfHealingEngine: Reusing proven episodic remedy ({cached_action.remediation_strategy.value})")
            return heuristic_diag, cached_action

        # 2. Run cognitive Root Cause Analysis (RCA)
        diag = await self.classifier.diagnose_fault(
            task_instruction=task_instruction,
            error_msg=error_msg,
            failed_output=failed_output,
            context=context,
        )

        # 3. Formulate strategy-specific healing action
        mutated_inputs = self.transmute_parameters(context)

        if diag.fault_category == FaultCategory.INPUT_FORMAT_ERROR:
            action = HealingAction(
                remediation_strategy=RemediationStrategy.MUTATE_PARAMS,
                revised_instruction=f"{task_instruction} (Input Transmuted & Normalized)",
                revised_inputs=mutated_inputs,
                explanation=f"Transmuted parameters to fix schema/format mismatch: {diag.root_cause_explanation}",
            )

        elif diag.fault_category in {FaultCategory.RATE_LIMITED_OR_BLOCKED, FaultCategory.TARGET_UNREACHABLE}:
            # Shift to passive OSINT reconnaissance (Wayback, Public DNS, BGP archives)
            action = HealingAction(
                remediation_strategy=RemediationStrategy.SHIFT_TO_PASSIVE_MIRROR,
                revised_instruction=f"Passively interrogate historical archives and DNS mirrors for {target_seed} (Bypassing target defenses)",
                revised_inputs={
                    **mutated_inputs,
                    "use_passive_fallback": True,
                    "passive_mirrors": ["wayback", "bgpview", "google_dns"],
                },
                target_tool_name="wayback_timeline" if specialist_name == "network_specialist" else specialist_name,
                explanation=f"Active connection blocked or rate-limited. Pivoted to passive OSINT archives: {diag.root_cause_explanation}",
            )

        elif diag.fault_category == FaultCategory.TOOL_DEFICIENCY:
            action = HealingAction(
                remediation_strategy=RemediationStrategy.SYNTHESIZE_TOOL,
                revised_instruction=f"Synthesize dynamic Python parser tool to extract target data for {task_instruction}",
                revised_inputs=mutated_inputs,
                synthesized_code_required=True,
                target_tool_name="toolmaker_specialist",
                explanation=f"Existing tools lack specific capability. Delegating to ToolmakerSpecialist for dynamic synthesis: {diag.root_cause_explanation}",
            )

        elif diag.fault_category == FaultCategory.CRITIC_REJECTION:
            action = HealingAction(
                remediation_strategy=RemediationStrategy.MUTATE_PARAMS,
                revised_instruction=f"Re-verify findings with rigorous secondary cross-correlation for {task_instruction}",
                revised_inputs={**mutated_inputs, "strict_verification": True},
                explanation="Evidence refuted by Critic. Re-executing with strict secondary cross-correlation.",
            )

        else:
            action = HealingAction(
                remediation_strategy=RemediationStrategy.EXPONENTIAL_BACKOFF,
                revised_instruction=task_instruction,
                revised_inputs=mutated_inputs,
                explanation="Transient execution failure. Re-attempting with cleaned parameters.",
            )

        return diag, action


# Global instance
self_healing_engine = SelfHealingEngine()

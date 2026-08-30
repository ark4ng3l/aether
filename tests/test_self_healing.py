"""
Tests for Autonomous Cognitive Self-Healing and Fault-Tolerance Subsystem in AETHER v4.0.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from aether.reasoning.self_healing import (
    CognitiveFaultClassifier,
    FaultCategory,
    RemediationStrategy,
    SelfHealingEngine,
    EpisodicFailureMemory,
    HealingAction,
    FaultDiagnosis,
    self_healing_engine,
)
from aether.reasoning.commander import CommanderAgent, SubTaskPlan
from aether.core.state import AgentState, EntityType, InvestigationStatus


class TestCognitiveFaultClassification:
    def test_waf_and_rate_limit_classification(self):
        """Identifies Cloudflare challenges and HTTP 429 rate limits as RATE_LIMITED_OR_BLOCKED."""
        diag_429 = CognitiveFaultClassifier.classify_heuristically("HTTP 429: Too Many Requests from origin", {})
        assert diag_429.fault_category == FaultCategory.RATE_LIMITED_OR_BLOCKED
        assert diag_429.suggested_strategy == RemediationStrategy.SHIFT_TO_PASSIVE_MIRROR

        diag_cf = CognitiveFaultClassifier.classify_heuristically("Access denied: Blocked by Cloudflare WAF", {})
        assert diag_cf.fault_category == FaultCategory.RATE_LIMITED_OR_BLOCKED

    def test_parameter_and_schema_mismatch_classification(self):
        """Identifies parameter formatting errors as INPUT_FORMAT_ERROR."""
        diag_fmt = CognitiveFaultClassifier.classify_heuristically("ValueError: Invalid domain format provided", {})
        assert diag_fmt.fault_category == FaultCategory.INPUT_FORMAT_ERROR
        assert diag_fmt.suggested_strategy == RemediationStrategy.MUTATE_PARAMS

    def test_timeout_and_unreachable_classification(self):
        """Identifies connection timeouts as TARGET_UNREACHABLE."""
        diag_timeout = CognitiveFaultClassifier.classify_heuristically("Connection timed out after 15000ms", {})
        assert diag_timeout.fault_category == FaultCategory.TARGET_UNREACHABLE
        assert diag_timeout.suggested_strategy == RemediationStrategy.SHIFT_TO_PASSIVE_MIRROR

    def test_tool_deficiency_classification(self):
        """Identifies missing parsers as TOOL_DEFICIENCY."""
        diag_tool = CognitiveFaultClassifier.classify_heuristically("No tool found to parse proprietary protocol stream", {})
        assert diag_tool.fault_category == FaultCategory.TOOL_DEFICIENCY
        assert diag_tool.suggested_strategy == RemediationStrategy.SYNTHESIZE_TOOL


class TestParameterTransmutation:
    def test_extract_clean_domain_from_full_url(self):
        """Extracts bare hostname from URL when tool expects domain parameter."""
        raw_ctx = {"domain": "https://threat.actor-site.com:8443/login/portal", "target": "https://threat.actor-site.com"}
        transmuted = SelfHealingEngine.transmute_parameters(raw_ctx)
        assert transmuted["domain"] == "threat.actor-site.com"

    def test_add_protocol_to_bare_url(self):
        """Prepends https:// to bare domain when tool expects URL parameter."""
        raw_ctx = {"url": "subdomain.target.org/api/v1"}
        transmuted = SelfHealingEngine.transmute_parameters(raw_ctx)
        assert transmuted["url"] == "https://subdomain.target.org/api/v1"

    def test_strip_cidr_notation_for_ip_tools(self):
        """Strips subnet mask from IP parameter."""
        raw_ctx = {"ip": "198.51.100.25/24"}
        transmuted = SelfHealingEngine.transmute_parameters(raw_ctx)
        assert transmuted["ip"] == "198.51.100.25"


class TestEpisodicFailureMemory:
    def test_memory_retrieval_and_clearing(self):
        """Stores proven remediation and enables retrieval by target & category."""
        mem = EpisodicFailureMemory()
        action = HealingAction(
            remediation_strategy=RemediationStrategy.SHIFT_TO_PASSIVE_MIRROR,
            revised_instruction="Query Wayback instead of direct HTTP",
            revised_inputs={"use_passive_fallback": True},
        )
        mem.record_successful_remediation(target="firewalled.corp", fault_category="rate_limited_or_blocked", action=action)

        cached = mem.get_proven_remediation(target="firewalled.corp", fault_category="rate_limited_or_blocked")
        assert cached is not None
        assert cached.remediation_strategy == RemediationStrategy.SHIFT_TO_PASSIVE_MIRROR

        # Non-matching target returns None
        assert mem.get_proven_remediation(target="other.corp", fault_category="rate_limited_or_blocked") is None


class TestCommanderAutonomousSelfHealing:
    @pytest.mark.asyncio
    async def test_commander_auto_heals_misformatted_task(self):
        """
        End-to-end test: Commander encounters a tool failure due to misformatted URL in domain field,
        diagnoses it, transmutes parameter to clean domain, and succeeds on the self-healing attempt.
        """
        state = AgentState(target_seed="target.com", target_type=EntityType.DOMAIN)
        commander = CommanderAgent(state=state)

        # Mock specialist that fails if given URL with 'https://', but succeeds if given clean domain
        mock_specialist = AsyncMock()
        async def mock_execute(instruction, context):
            dom = context.get("domain", "")
            if "https://" in dom:
                return {"success": False, "error": "ValueError: Invalid domain format containing protocol"}
            return {"success": True, "data": {"resolved_ip": "93.184.216.34"}, "summary": "Resolved clean domain"}

        mock_specialist.execute_specialized_task = mock_execute
        commander.specialists["network_specialist"] = mock_specialist

        task = SubTaskPlan(
            task_id="task_heal_test",
            specialist="network_specialist",
            instruction="Resolve perimeter DNS records",
            context_inputs={"domain": "https://target.com/login"},
        )

        res = await commander._execute_and_verify_task(task)
        assert res.get("success") is True
        assert res.get("healed") is True
        assert res.get("strategy") == "mutate_params"
        assert "93.184.216.34" in str(res.get("data"))

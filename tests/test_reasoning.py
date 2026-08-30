"""Tests for aether.reasoning — Planner, Hypothesis, Critic."""

import pytest
from unittest.mock import patch, AsyncMock
from aether.core.state import AgentState, Entity, EntityType, InvestigationStatus
from aether.reasoning.planner import Planner, PlanAction
from aether.reasoning.hypothesis import HypothesisEngine
from aether.reasoning.critic import RedTeamCritic, CriticVerdict


class TestPlanner:
    @pytest.mark.asyncio
    async def test_queue_consumption(self):
        state = AgentState(investigation_id="test-plan-1", target_seed="testuser")
        state.current_task_stack.append("social: @testuser")
        planner = Planner(state)

        action = await planner.plan_next_step()
        assert action is not None
        assert action.action == "tool_call"
        assert action.tool_name == "social_recon"
        assert action.params == {"username": "@testuser"}

    @pytest.mark.asyncio
    async def test_dead_end_detection(self):
        state = AgentState(investigation_id="test-plan-2", target_seed="testuser")
        state.add_entity(Entity(id="e1", type=EntityType.PERSON))
        planner = Planner(state)
        planner._previous_entity_count = 1  # Gain = 0
        planner._stagnant_steps = 2         # Next zero-gain step reaches threshold of 3

        action = await planner.plan_next_step()
        assert action is not None
        assert action.action == "hypothesis"

    @pytest.mark.asyncio
    @patch("aether.core.model_manager.model_manager.call_model")
    async def test_llm_plan_generation(self, mock_call):
        mock_call.return_value = PlanAction(
            action="tool_call",
            tool_name="web_search",
            params={"query": "test query"},
            reasoning="Testing LLM planner",
        )
        state = AgentState(investigation_id="test-plan-3", target_seed="target")
        planner = Planner(state)

        action = await planner.plan_next_step()
        assert action is not None
        assert action.tool_name == "web_search"
        assert action.params["query"] == "test query"


class TestHypothesisEngine:
    @pytest.mark.asyncio
    @patch("aether.core.model_manager.model_manager.call_model")
    async def test_generate_hypotheses(self, mock_call):
        mock_call.return_value = (
            "POSSIBLE: Check GitHub repos for email leak\n"
            "POSSIBLE: Search domain WHOIS history\n"
            "POSSIBLE: Verify LinkedIn company affiliation"
        )
        engine = HypothesisEngine()
        hypotheses = await engine.generate_abductive_hypotheses([{"desc": "target", "type": "person"}])
        assert len(hypotheses) == 3
        assert "Check GitHub repos for email leak" in hypotheses[0]


class TestRedTeamCritic:
    @pytest.mark.asyncio
    @patch("aether.core.model_manager.model_manager.call_model")
    async def test_evaluate_finding(self, mock_call):
        mock_call.return_value = CriticVerdict(
            verdict="CONFIRMED",
            reasoning="Solid evidence across 2 sources.",
            confidence=0.9,
        )
        critic = RedTeamCritic()
        verdict = await critic.evaluate_finding("Found matching GitHub account")
        assert verdict["verdict"] == "CONFIRMED"
        assert verdict["confidence"] == 0.9

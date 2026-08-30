"""
Comprehensive Test Suite for AETHER v4.0 Architecture:
- AST Code Sandbox & Security Policies
- GraphRAG & Hybrid Memory Knowledge System
- Multimodal Perception (VLM, Whisper, GeoCorrelator)
- Specialist Agent Plugins (Network, Vision, Audio, Toolmaker)
- Commander Agent Hierarchical Task Decomposition & Self-Correction
"""

import pytest
import asyncio
from typing import Dict, Any

from aether.core.state import AgentState, Entity, EntityType, InvestigationStatus
from aether.perception.tools.sandbox import ASTCodeSandbox, SecurityPolicyViolation
from aether.memory.graph_rag import GraphRAGKnowledgeEngine
from aether.memory.hybrid_store import HybridKnowledgeStore
from aether.perception.multimodal.geo_correlator import GeoCorrelator
from aether.perception.multimodal.audio_engine import WhisperAudioPipeline
from aether.perception.multimodal.vlm_engine import VisionLanguageIntelligenceEngine
from aether.perception.chains.pipeline_chainer import PipelineChainer
from aether.reasoning.specialists.network_specialist import network_specialist
from aether.reasoning.specialists.vision_specialist import vision_specialist
from aether.reasoning.specialists.audio_specialist import audio_specialist
from aether.reasoning.specialists.toolmaker_specialist import toolmaker_specialist
from aether.reasoning.commander import CommanderAgent, PlanTreeDecomposition, SubTaskPlan
from aether.reasoning.self_correction import self_correction_engine, SelfCorrectionPlan
from unittest.mock import patch, AsyncMock


# ── 1. AST Code Sandbox Tests ──────────────────────────────────────────────────

class TestASTCodeSandbox:
    """Validates AST static security analysis and execution constraints."""

    def test_sandbox_accepts_valid_safe_code(self):
        safe_code = (
            "def run_calculation(x: int, y: int):\n"
            "    return {'sum': x + y, 'product': x * y}\n"
        )
        is_safe, err = ASTCodeSandbox.validate_source(safe_code)
        assert is_safe is True
        assert err is None

        result = ASTCodeSandbox.execute_sandboxed_tool(
            source_code=safe_code,
            entrypoint="run_calculation",
            params={"x": 5, "y": 10},
        )
        assert result == {"sum": 15, "product": 50}

    def test_sandbox_rejects_forbidden_imports(self):
        unsafe_codes = [
            "import os\ndef test(): os.system('dir')",
            "import sys\ndef test(): sys.exit()",
            "import subprocess\ndef test(): subprocess.run(['calc'])",
            "from shutil import rmtree\ndef test(): pass",
            "import ctypes\ndef test(): pass",
            "import pickle\ndef test(): pass",
        ]
        for code in unsafe_codes:
            is_safe, err = ASTCodeSandbox.validate_source(code)
            assert is_safe is False
            assert "Prohibited" in str(err)

    def test_sandbox_rejects_forbidden_builtins(self):
        unsafe_calls = [
            "def test(): return eval('2 + 2')",
            "def test(): return exec('x = 1')",
            "def test(): return open('file.txt', 'r')",
            "def test(): return __import__('os')",
            "def test(): return globals()",
        ]
        for code in unsafe_calls:
            is_safe, err = ASTCodeSandbox.validate_source(code)
            assert is_safe is False
            assert "Prohibited" in str(err)

    def test_sandbox_raises_security_exception_on_execution(self):
        unsafe_code = "import os\ndef run(): pass"
        with pytest.raises(SecurityPolicyViolation):
            ASTCodeSandbox.execute_sandboxed_tool(unsafe_code, "run", {})


# ── 2. GraphRAG & Hybrid Memory Tests ──────────────────────────────────────────

class TestGraphRAGAndHybridMemory:
    """Validates multi-hop graph retrieval and hybrid Vector+Graph store."""

    def test_graph_rag_node_and_edge_relations(self):
        graph = GraphRAGKnowledgeEngine()
        graph.clear()

        # Add entities
        e1 = Entity(id="target.com", type=EntityType.DOMAIN, properties={"name": "target.com"}, confidence=1.0)
        e2 = Entity(id="198.51.100.1", type=EntityType.IP_ADDRESS, properties={"name": "198.51.100.1"}, confidence=0.95)
        e3 = Entity(id="AS12345", type=EntityType.COMPANY, properties={"name": "AS12345 Cloud Provider"}, confidence=0.90)

        graph.add_entity(e1)
        graph.add_entity(e2)
        graph.add_entity(e3)

        # Add relations: domain -> resolves_to -> IP -> hosted_by -> ASN
        graph.add_relation(e1.id, e2.id, relation_type="RESOLVES_TO", confidence=0.95)
        graph.add_relation(e2.id, e3.id, relation_type="HOSTED_BY", confidence=0.90)

        # Query 2-hop subgraph from domain
        subgraph = graph.get_multihop_subgraph(e1.id, max_hops=2)
        assert subgraph["node_count"] >= 3
        assert subgraph["edge_count"] >= 2
        assert len(subgraph["triplets"]) >= 2
        assert "RESOLVES_TO" in subgraph["prompt_context"]

    def test_hybrid_knowledge_store_fusion(self):
        hybrid = HybridKnowledgeStore()
        hybrid.clear()

        e = Entity(id="example.com", type=EntityType.DOMAIN, properties={"name": "example.com"})
        hybrid.ingest_finding(
            finding_id="finding_dns_1",
            text="Domain example.com resolves to 93.184.216.34 under EDGECAST network.",
            entity=e,
        )

        fused = hybrid.query_fused_context(
            query="example.com network infrastructure",
            root_entity_id=e.id,
        )
        assert isinstance(fused.synthesized_prompt_context, str)
        assert len(fused.synthesized_prompt_context) > 0


# ── 3. Multimodal Perception Tests ─────────────────────────────────────────────

class TestMultimodalPerception:
    """Validates EXIF GPS parsing, Whisper pipeline, and VLM fallback."""

    def test_geo_correlator_missing_file_handling(self):
        res = GeoCorrelator.extract_gps("non_existent_image.jpg")
        assert res["found"] is False
        assert "error" in res

    @pytest.mark.asyncio
    async def test_whisper_audio_pipeline_handling(self):
        pipeline = WhisperAudioPipeline()
        res = await pipeline.transcribe("non_existent_audio.wav")
        assert res["success"] is False

    @pytest.mark.asyncio
    async def test_vlm_engine_missing_file_handling(self):
        vlm = VisionLanguageIntelligenceEngine()
        res = await vlm.analyze_image("non_existent_photo.png")
        assert res["success"] is False


# ── 4. Pipeline Chainer Tests ──────────────────────────────────────────────────

class TestPipelineChainer:
    """Validates automatic entity extraction and chaining between tools."""

    def test_extract_chainable_targets(self):
        sample_data = {
            "subdomains": ["api.example.com", "auth.example.com"],
            "ips": ["93.184.216.34", "1.1.1.1"],
            "admin_email": "security@example.com",
        }
        targets = PipelineChainer.extract_chainable_targets(sample_data)
        assert "93.184.216.34" in targets["ips"]
        assert "api.example.com" in targets["domains"]
        assert "security@example.com" in targets["emails"]


# ── 5. Specialist Agents Tests ─────────────────────────────────────────────────

class TestSpecialistAgents:
    """Validates domain-specific execution across all 4 specialists."""

    @pytest.mark.asyncio
    async def test_network_specialist_execution(self):
        res = await network_specialist.execute_specialized_task(
            instruction="Perform DNS lookup on domain",
            context={"domain": "example.com"},
        )
        assert isinstance(res, dict)
        assert "success" in res

    @pytest.mark.asyncio
    @patch("aether.core.model_manager.model_manager.call_model")
    async def test_toolmaker_specialist_safe_synthesis(self, mock_call):
        from aether.reasoning.specialists.toolmaker_specialist import SynthesizedToolSchema
        mock_call.return_value = SynthesizedToolSchema(
            tool_name="hash_computer",
            description="Computes SHA256 of domain",
            entrypoint="compute_hash",
            python_code=(
                "import hashlib\n"
                "def compute_hash(**kwargs):\n"
                "    val = kwargs.get('domain', '')\n"
                "    return {'hash': hashlib.sha256(val.encode()).hexdigest()}\n"
            ),
            example_input="example.com",
        )
        res = await toolmaker_specialist.execute_specialized_task(
            instruction="Compute hash of domain string",
            context={"domain": "example.com"},
        )
        assert isinstance(res, dict)
        assert res.get("success") is True
        assert "hash" in res.get("data", {})

# ── 6. Commander Agent & Self-Correction Tests ─────────────────────────────────

class TestCommanderAgentAndSelfCorrection:
    """Validates Commander task decomposition and ReAct self-correction loop."""

    @pytest.mark.asyncio
    @patch("aether.core.model_manager.model_manager.call_model")
    async def test_commander_task_decomposition(self, mock_call):
        mock_call.return_value = PlanTreeDecomposition(
            goal_summary="Investigate domain perimeter",
            tree_reasoning="Decomposing into DNS enumeration",
            subtasks=[
                SubTaskPlan(
                    task_id="task_dns",
                    specialist="network_specialist",
                    instruction="Run DNS enum on example.com",
                    context_inputs={"domain": "example.com"},
                    dependencies=[],
                )
            ]
        )
        state = AgentState(
            investigation_id="test_inv_1",
            project_id="test_proj_1",
            target_seed="example.com",
            target_type=EntityType.DOMAIN,
        )
        commander = CommanderAgent(state=state)

        subtasks = await commander.decompose_goal("Investigate domain perimeter")
        assert len(subtasks) >= 1
        assert all(isinstance(t, SubTaskPlan) for t in subtasks)

    @pytest.mark.asyncio
    @patch("aether.core.model_manager.model_manager.call_model")
    async def test_self_correction_engine_formulation(self, mock_call):
        mock_call.return_value = SelfCorrectionPlan(
            root_cause="Firewall block detected",
            adjustment_strategy="parameter_refinement",
            revised_instruction="Query secondary DNS mirror for example.com",
            revised_inputs={"domain": "example.com", "use_mirror": True},
        )
        correction = await self_correction_engine.formulate_correction(
            task_instruction="Enumerate hidden subdomains",
            failed_output={"data": "403 Forbidden"},
            critic_reasoning="Blocked by target firewall",
            context={"domain": "example.com"},
        )
        assert correction.adjustment_strategy in {"parameter_refinement", "tool_pivot", "query_broadening"}
    @pytest.mark.asyncio
    @patch("aether.core.model_manager.model_manager.call_model")
    @patch("aether.reasoning.critic.RedTeamCritic.evaluate_finding")
    async def test_commander_mission_lifecycle(self, mock_critic, mock_call):
        from aether.reasoning.critic import CriticVerdict
        mock_critic.return_value = CriticVerdict(
            verdict="CONFIRMED",
            reasoning="Direct evidence verified",
            confidence=0.95,
        )
        mock_call.return_value = PlanTreeDecomposition(
            goal_summary="Preliminary perimeter reconnaissance",
            tree_reasoning="Quick port/dns sweep",
            subtasks=[
                SubTaskPlan(
                    task_id="task_sweep",
                    specialist="network_specialist",
                    instruction="Run basic whois lookup",
                    context_inputs={"domain": "example.com"},
                )
            ]
        )
        state = AgentState(
            investigation_id="test_inv_2",
            project_id="test_proj_2",
            target_seed="example.com",
            target_type=EntityType.DOMAIN,
        )
        commander = CommanderAgent(state=state)

        await commander.execute_mission("Preliminary perimeter reconnaissance")
        assert state.status == InvestigationStatus.COMPLETED
        assert len(state.completed_tasks) >= 1

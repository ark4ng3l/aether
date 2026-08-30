"""
Tests for Multi-Signal Confidence Scoring Algorithm (§A.2).
Formula:
  final_confidence = clamp(0, 1,
      base_llm_critic_score * 0.4
    + deterministic_format_score * 0.2
    + corroboration_bonus * 0.3
    + source_reliability_avg * 0.1
  )
"""

import pytest
from aether.core.state import Entity, EntityType, ConfidenceSignal
from aether.memory.entity_resolver import EntityResolver, SOURCE_RELIABILITY
from aether.memory.graph_store import GraphStore


@pytest.fixture
def resolver(tmp_path):
    db_file = tmp_path / "test_graph.db"
    store = GraphStore(db_path=str(db_file))
    return EntityResolver(graph_store=store)


class TestConfidenceScoring:
    def test_single_source_default(self, resolver):
        """Single source, perfect format, average critic score."""
        score, signals, breakdown = resolver.calculate_confidence(
            source_tool="whois_lookup",
            corroboration_count=1,
            critic_confidence=0.5,
            deterministic_format_score=1.0,
        )
        # whois reliability = 0.95
        # (0.5 * 0.4) + (1.0 * 0.2) + (0.0 * 0.3) + (0.95 * 0.1) = 0.2 + 0.2 + 0.0 + 0.095 = 0.495
        assert score == pytest.approx(0.49, abs=0.02)
        assert breakdown["tier"] == "PLAUSIBLE"
        assert len(signals) == 4
        assert any(s.source_tool == "whois_lookup" for s in signals)

    def test_corroborated_confirmed(self, resolver):
        """Corroborated across 3 tools with high critic confidence."""
        score, signals, breakdown = resolver.calculate_confidence(
            source_tool="whois_lookup",
            corroboration_count=3,
            critic_confidence=0.9,
            deterministic_format_score=1.0,
        )
        # corroboration_bonus = min(0.3, (3-1)*0.15) = 0.3
        # (0.9 * 0.4) + (1.0 * 0.2) + (0.3 * 0.3) + (0.95 * 0.1) = 0.36 + 0.2 + 0.09 + 0.095 = 0.745
        assert score == pytest.approx(0.74, abs=0.02)
        assert breakdown["tier"] == "CONFIRMED"

    def test_low_critic_rejected(self, resolver):
        """Low critic confidence and poor formatting yields rejection."""
        score, signals, breakdown = resolver.calculate_confidence(
            source_tool="web_search",
            corroboration_count=1,
            critic_confidence=0.1,
            deterministic_format_score=0.2,
        )
        # web_search reliability = 0.70
        # (0.1 * 0.4) + (0.2 * 0.2) + (0.0 * 0.3) + (0.70 * 0.1) = 0.04 + 0.04 + 0.0 + 0.07 = 0.15
        assert score == pytest.approx(0.15, abs=0.01)
        assert breakdown["tier"] == "REJECTED"

    def test_clamping_upper_bound(self, resolver):
        """Values cannot exceed 1.0."""
        score, signals, breakdown = resolver.calculate_confidence(
            source_tool="whois_lookup",
            corroboration_count=5,
            critic_confidence=1.0,
            deterministic_format_score=1.0,
        )
        assert score <= 1.0
        assert score >= 0.0

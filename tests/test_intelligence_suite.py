"""
Comprehensive test suite for AETHER Advanced Intelligence & Forensic Analytics.
Covers EntityResolver, StylometryAnalyzer, TemporalRhythmEstimator, AdmiraltyRating,
Perception Tools, and API Endpoints.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from aether.reasoning.entity_resolver import (
    entity_resolver,
    stylometry_analyzer,
    temporal_estimator,
    AdmiraltyRating,
)
from aether.perception.tools.intelligence_tools import (
    EntityResolutionTool,
    StylometryTool,
    TemporalRhythmTool,
)
from aether.api.server import app
import aether.api.server as server_module


@pytest.fixture
def client():
    return TestClient(app, headers={"Authorization": f"Bearer {server_module.AUTH_TOKEN}"})


class TestEntityResolver:
    def test_high_similarity_match(self):
        prof_a = {
            "username": "alex_cyber",
            "name": "Alex Vance",
            "bio": "Cybersecurity researcher and Python developer exploring OSINT",
            "location": "Berlin, Germany",
        }
        prof_b = {
            "username": "alex_cyber_dev",
            "name": "Alex V.",
            "bio": "Security researcher building Python OSINT and threat intel tools",
            "location": "Berlin",
        }
        result = entity_resolver.resolve_profiles(prof_a, prof_b)
        assert result.overall_confidence >= 0.65
        assert "CONFIRMED_MATCH" in result.verdict or "HIGH_PROBABILITY" in result.verdict
        assert result.location_match is True
        assert len(result.evidence_breakdown) >= 2

    def test_unrelated_entities(self):
        prof_a = {
            "username": "john_doe_99",
            "name": "John Doe",
            "bio": "Chef and foodie traveling the world",
            "location": "New York",
        }
        prof_b = {
            "username": "crypto_trader_x",
            "name": "Satoshi N.",
            "bio": "Bitcoin maximalist and DeFi enthusiast",
            "location": "Tokyo",
        }
        result = entity_resolver.resolve_profiles(prof_a, prof_b)
        assert result.overall_confidence < 0.40
        assert "INSUFFICIENT_CORRELATION" in result.verdict or "POSSIBLE_ASSOCIATION" in result.verdict


class TestStylometryAnalyzer:
    def test_feature_extraction(self):
        text = "This is a detailed forensic sample. We analyze the linguistic patterns carefully! #OSINT"
        features = stylometry_analyzer.extract_features(text)
        assert features["word_count"] > 5
        assert features["ttr_lexical_diversity"] > 0.0
        assert features["punctuation_density"] > 0.0

    def test_authorship_comparison_similar(self):
        sample_a = "Security investigations require careful analysis of digital artifacts. We must verify all IOCs and DNS records rigorously."
        sample_b = "Threat investigations require thorough analysis of digital footprints. We verify all threat intelligence and IP records carefully."
        res = stylometry_analyzer.compare_authorship(sample_a, sample_b)
        assert res["authorship_similarity_pct"] >= 60.0
        assert "SIMILARITY" in res["verdict"]

    def test_insufficient_data(self):
        res = stylometry_analyzer.compare_authorship("Too short", "Also short")
        assert "INSUFFICIENT_DATA" in res["verdict"]


class TestTemporalRhythmEstimator:
    def test_timezone_inference(self):
        # Create timestamps simulating activity mostly during UTC 08:00 - 20:00 (rest 23:00 - 05:00 UTC)
        timestamps = [
            f"2026-08-30T{h:02d}:15:00Z"
            for h in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        ] * 3
        res = temporal_estimator.estimate_timezone(timestamps)
        assert "estimated_timezone" in res
        assert res["total_analyzed_events"] == 39
        assert res["confidence"] == "HIGH"
        assert len(res["hourly_histogram_utc"]) == 24


class TestAdmiraltySystem:
    def test_admiralty_evaluations(self):
        r1 = AdmiraltyRating.evaluate("dns_lookup", corroborated_count=3, is_authoritative=True)
        assert r1.source_grade == "A"
        assert r1.info_grade == "1"
        assert r1.rating_code == "A1"

        r2 = AdmiraltyRating.evaluate("paste_dump", corroborated_count=1)
        assert r2.source_grade == "D"
        assert r2.info_grade == "3"
        assert r2.rating_code == "D3"


class TestPerceptionToolsExecution:
    @pytest.mark.asyncio
    async def test_entity_resolution_tool(self):
        tool = EntityResolutionTool()
        res = await tool.execute(
            profile_a={"username": "bob_sec", "bio": "Security engineer"},
            profile_b={"username": "bob_sec", "bio": "Security engineer"},
        )
        assert res.success is True
        assert res.data["overall_confidence_pct"] >= 80.0

    @pytest.mark.asyncio
    async def test_stylometry_tool(self):
        tool = StylometryTool()
        res = await tool.execute(
            sample_a="This is a forensic sample with rich vocabulary and consistent punctuation patterns.",
            sample_b="This is another forensic sample containing detailed linguistic markers and punctuation.",
        )
        assert res.success is True
        assert "authorship_similarity_pct" in res.data

    @pytest.mark.asyncio
    async def test_temporal_tool(self):
        tool = TemporalRhythmTool()
        res = await tool.execute(timestamps=["2026-08-30T10:00:00Z", "2026-08-30T11:00:00Z", "2026-08-30T12:00:00Z", "2026-08-30T13:00:00Z", "2026-08-30T14:00:00Z"])
        assert res.success is True
        assert "estimated_timezone" in res.data


class TestServerIntelligenceEndpoints:
    def test_resolve_entities_endpoint(self, client: TestClient):
        resp = client.post("/api/intelligence/resolve-entities", json={
            "profile_a": {"username": "charlie_hacker", "location": "London"},
            "profile_b": {"username": "charlie_hacker", "location": "London, UK"}
        })
        assert resp.status_code == 200
        assert "overall_confidence_pct" in resp.json()

    def test_stylometry_endpoint(self, client: TestClient):
        resp = client.post("/api/intelligence/stylometry", json={
            "sample_a": "Threat actor communication sample analyzing C2 protocols and beacon intervals.",
            "sample_b": "Threat actor forum post discussing beacon intervals and C2 server configurations."
        })
        assert resp.status_code == 200
        assert "authorship_similarity_pct" in resp.json()

    def test_temporal_rhythm_endpoint(self, client: TestClient):
        resp = client.post("/api/intelligence/temporal-rhythm", json={
            "timestamps": ["2026-08-30T08:00:00Z", "2026-08-30T12:00:00Z", "2026-08-30T16:00:00Z", "2026-08-30T18:00:00Z", "2026-08-30T20:00:00Z"]
        })
        assert resp.status_code == 200
        assert "estimated_timezone" in resp.json()

"""
Comprehensive Test Suite for Full-Spectrum OSINT & Cyber Intelligence Engine.

Tests:
1. HandlePermutationGenerator (Social-Analyzer / Maigret)
2. AvatarPerceptualComparator (Image Hashing & Hamming Distance)
3. ProfilePIIExtractor (Crypto, Phone, Email, Telegram)
4. WebCheckSuite (DNS, SSL, Standards, Redirects, WAF, Carbon)
5. CyberFrameworksEngine (MITRE ATT&CK v19.1, D3FEND, Fight Fraud F3)
6. SunChronolocator (Solar ephemeris & shadow inverse chronolocation)
7. Server API Endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from aether.api.server import app
import aether.api.server as server_module

from aether.reasoning.handle_permutator import handle_permutator
from aether.reasoning.avatar_comparator import avatar_comparator
from aether.reasoning.cyber_frameworks import cyber_frameworks
from aether.perception.tools.social_matrix_tools import profile_pii_extractor
from aether.perception.tools.geospatial_intelligence import sun_chronolocator
from aether.perception.tools.web_check_suite import carbon_footprint_estimator


@pytest.fixture
def client():
    return TestClient(app, headers={"Authorization": f"Bearer {server_module.AUTH_TOKEN}"})


class TestHandlePermutator:
    def test_permutations_generation(self):
        perms = handle_permutator.generate(
            first_name="John",
            last_name="Doe",
            birth_year=1995,
            company="Acme",
            limit=50,
        )
        assert len(perms) > 10
        assert "johndoe" in perms
        assert "john.doe" in perms or "john_doe" in perms
        assert any("95" in p or "1995" in p for p in perms)

    def test_leetspeak_mutations(self):
        leet = handle_permutator._generate_leetspeak("shadow")
        assert any("5hadow" in l or "sh4dow" in l or "shad0w" in l for l in leet)


class TestAvatarComparator:
    def test_exact_hash_match(self):
        h = "a1b2c3d4e5f60718"
        res = avatar_comparator.compare_hashes(h, h)
        assert res["hamming_distance"] == 0
        assert res["similarity_pct"] == 100.0
        assert res["is_match"] is True
        assert res["verdict"] == "EXACT_MATCH"

    def test_similar_hash_match(self):
        h1 = "ffff0000ffff0000"
        h2 = "ffff0000ffff0001"  # 1 bit difference
        res = avatar_comparator.compare_hashes(h1, h2)
        assert res["hamming_distance"] == 1
        assert res["is_match"] is True
        assert res["verdict"] == "HIGH_CONFIDENCE_MATCH"

    def test_distinct_hashes(self):
        h1 = "0000000000000000"
        h2 = "ffffffffffffffff"  # 64 bits difference
        res = avatar_comparator.compare_hashes(h1, h2)
        assert res["hamming_distance"] == 64
        assert res["similarity_pct"] == 0.0
        assert res["is_match"] is False
        assert res["verdict"] == "DISTINCT_AVATAR"


class TestProfilePIIExtractor:
    def test_pii_extraction(self):
        sample_bio = (
            "Lead dev @acme. Contact me: alex@secops.io or +1-555-019-2834. "
            "Tips in BTC: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa or ETH: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045. "
            "TG: @alex_crypto"
        )
        res = profile_pii_extractor(sample_bio)
        assert res["success"] is True
        assert "alex@secops.io" in res["emails"]
        assert "bitcoin" in res["crypto_wallets"]
        assert "ethereum" in res["crypto_wallets"]
        assert len(res["phone_numbers"]) >= 1
        assert "alex_crypto" in res["telegram_handles"]


class TestCyberFrameworks:
    def test_framework_mapping(self):
        findings = "Discovered open DNS records, synthetic identity cluster and crypto wallet 0x123 for money mule layering."
        mappings = cyber_frameworks.map_findings(findings, discovered_types=["domain", "crypto_wallet"])
        assert len(mappings) > 0
        tech_ids = [m.technique_id for m in mappings]
        assert "T1590.001" in tech_ids  # ATT&CK DNS Recon
        assert "F1021" in tech_ids      # F3 Crypto Off-ramping
        assert "F1001" in tech_ids      # F3 Synthetic Identity

    def test_frameworks_summary(self):
        summary = cyber_frameworks.get_matrix_summary()
        assert "frameworks" in summary
        assert len(summary["frameworks"]) == 3
        assert summary["total_supported_techniques"] > 20


class TestSunChronolocator:
    def test_forward_solar_position(self):
        # Summer solstice noon in Greenwich (lat 51.48, lon 0.0)
        res = sun_chronolocator(
            latitude=51.48,
            longitude=0.0,
            utc_timestamp="2026-06-21T12:00:00Z",
        )
        assert res["success"] is True
        assert res["is_daylight"] is True
        assert res["solar_elevation_deg"] > 50.0  # High sun at noon in June

    def test_inverse_shadow_estimation(self):
        # 10m pole casting 10m shadow -> elevation ~45 degrees
        res = sun_chronolocator(
            latitude=35.68,
            longitude=51.38,
            shadow_length_meters=10.0,
            object_height_meters=10.0,
            target_date="2026-06-21",
        )
        assert res["success"] is True
        assert res["mode"] == "INVERSE_SHADOW_ESTIMATION"
        assert len(res["possible_capture_times"]) > 0


class TestCarbonFootprintEstimator:
    def test_carbon_calculation(self):
        res = carbon_footprint_estimator(transfer_size_kb=1500.0, is_green_host=True)
        assert res["success"] is True
        assert res["co2_grams_per_visit"] > 0.0
        assert res["eco_rating"] in ["A+", "A", "B", "C"]


class TestFullSpectrumServerEndpoints:
    def test_permutations_api(self, client: TestClient):
        resp = client.post("/api/intelligence/permutations", json={"first_name": "Alice", "last_name": "Smith"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert len(resp.json()["permutations"]) > 5

    def test_avatar_match_api(self, client: TestClient):
        resp = client.post("/api/intelligence/avatar-match", json={"hash_a": "1234567812345678", "hash_b": "1234567812345678"})
        assert resp.status_code == 200
        assert resp.json()["is_match"] is True

    def test_chronolocate_api(self, client: TestClient):
        resp = client.post("/api/intelligence/chronolocate", json={"latitude": 35.68, "longitude": 51.38})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_cyber_frameworks_summary_api(self, client: TestClient):
        resp = client.get("/api/intelligence/frameworks/mitre")
        assert resp.status_code == 200
        assert "frameworks" in resp.json()

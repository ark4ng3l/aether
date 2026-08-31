"""
Unit and Integration Tests for AETHER Next-Generation Cyber Intelligence Capabilities:
1. DarkNet & Ransomware Leaks Tracker
2. AI Deepfake & Synthetic Persona Forensics
3. Executive Dossier & HTML/STIX Exporter
4. Continuous Surveillance Watcher Engine
5. Graph Centrality & Hidden Linkage Analytics
"""

from __future__ import annotations

import io
import base64
import pytest
from PIL import Image
from starlette.testclient import TestClient

from aether.api.server import app, AUTH_TOKEN
from aether.perception.tools.darknet_ransomware_tracker import ransomware_leak_hunter, darknet_mention_scanner
from aether.perception.tools.synthetic_persona_forensics import ela_forensic_analyzer, gan_artifact_detector
from aether.reasoning.executive_dossier_exporter import ExecutiveDossierExporter
from aether.core.continuous_watcher import ContinuousWatcherManager
from aether.reasoning.graph_analytics import GraphCentralityEngine


@pytest.fixture
def auth_client():
    return TestClient(app, headers={"Authorization": f"Bearer {AUTH_TOKEN}"})


@pytest.fixture
def sample_image_base64() -> str:
    img = Image.new("RGB", (256, 256), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── 1. DarkNet & Ransomware Tracker Tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_ransomware_leak_hunter_structure():
    res = await ransomware_leak_hunter("test-target-corp.com")
    assert res["success"] is True
    assert "is_breached_or_extorted" in res
    assert "total_extortion_entries" in res
    assert "risk_level" in res


@pytest.mark.asyncio
async def test_darknet_mention_scanner_validation():
    res = await darknet_mention_scanner("target_credential")
    assert res["success"] is True
    assert "total_darknet_results" in res


# ── 2. AI Deepfake & Synthetic Persona Forensics Tests ────────────────────────

def test_ela_forensic_analyzer(sample_image_base64):
    res = ela_forensic_analyzer(sample_image_base64)
    assert res["success"] is True
    assert "mean_error_level" in res
    assert "tamper_probability_pct" in res
    assert "verdict" in res


def test_gan_artifact_detector(sample_image_base64):
    res = gan_artifact_detector(sample_image_base64)
    assert res["success"] is True
    assert "synthetic_face_probability_pct" in res
    assert "center_to_border_entropy_ratio" in res
    assert "is_likely_ai_generated" in res


# ── 3. Executive Dossier & Exporter Tests ──────────────────────────────────────

def test_executive_dossier_exporter_html_generation():
    dummy_project = {
        "name": "Operation Cobalt Shadow",
        "target_seed": "apt29-infil.org",
        "target_type": "domain",
        "context_briefing": "State-sponsored infrastructure analysis",
        "entities_count": 2,
        "dossier": "Confirmed malicious command and control server.",
        "state": {
            "entities": {
                "e1": {"name": "198.51.100.1", "type": "ip_address", "confidence": 0.95, "signals": ["DNS", "BGP"]},
                "e2": {"name": "admin@apt29-infil.org", "type": "email", "confidence": 0.88, "signals": ["WHOIS"]},
            },
            "relationships": [
                {"source_id": "e1", "target_id": "e2", "relation_type": "RESOLVES_TO"}
            ],
        },
    }
    html = ExecutiveDossierExporter.generate_html_report(dummy_project, {"type": "bundle", "objects": []})
    assert "<!DOCTYPE html>" in html
    assert "Operation Cobalt Shadow" in html
    assert "apt29-infil.org" in html
    assert "198.51.100.1" in html
    assert "application/ld+json" in html


# ── 4. Continuous Surveillance Watcher Tests ──────────────────────────────────

def test_continuous_watcher_crud(tmp_path):
    wm = ContinuousWatcherManager(db_path=tmp_path / "test_watcher.db")
    watcher = wm.add_watcher("critical-asset.com", "domain", interval_minutes=30)
    assert watcher["id"] is not None
    assert watcher["target"] == "critical-asset.com"

    watchers = wm.list_watchers()
    assert len(watchers) == 1

    deleted = wm.delete_watcher(watcher["id"])
    assert deleted is True
    assert len(wm.list_watchers()) == 0


# ── 5. Graph Centrality & Linkage Analytics Tests ─────────────────────────────

def test_graph_centrality_analytics():
    entities = {
        "node_a": {"name": "Threat Actor X", "type": "person"},
        "node_b": {"name": "C2 Server 1", "type": "ip_address"},
        "node_c": {"name": "C2 Server 2", "type": "ip_address"},
        "node_d": {"name": "Victim Bank", "type": "organization"},
    }
    relationships = [
        {"source_id": "node_a", "target_id": "node_b", "relation_type": "OPERATES"},
        {"source_id": "node_a", "target_id": "node_c", "relation_type": "OPERATES"},
        {"source_id": "node_b", "target_id": "node_d", "relation_type": "TARGETS"},
    ]

    res = GraphCentralityEngine.analyze_graph(entities, relationships)
    assert res["total_nodes"] == 4
    assert res["total_edges"] == 3
    assert len(res["centrality_rankings"]) == 4
    assert res["most_influential_node"] is not None
    # node_a or node_b should be highest centrality
    top_node = res["most_influential_node"]["id"]
    assert top_node in ("node_a", "node_b")


# ── 6. Next-Gen API Server Endpoints Tests ────────────────────────────────────

def test_server_ransomware_leaks_endpoint(auth_client):
    resp = auth_client.post("/api/intelligence/ransomware-leaks", json={"target": "tesla.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_server_deepfake_forensics_endpoint(auth_client, sample_image_base64):
    resp = auth_client.post("/api/intelligence/forensics/deepfake", json={"image_bytes_base64": sample_image_base64})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "error_level_analysis" in data
    assert "gan_synthesis_analysis" in data


def test_server_graph_centrality_endpoint(auth_client):
    payload = {
        "entities": {
            "n1": {"name": "Actor 1", "type": "person"},
            "n2": {"name": "Server 1", "type": "ip_address"},
        },
        "relationships": [
            {"source_id": "n1", "target_id": "n2", "relation_type": "CONNECTS_TO"}
        ],
    }
    resp = auth_client.post("/api/intelligence/graph/centrality", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_nodes"] == 2
    assert data["total_edges"] == 1


def test_server_watchers_lifecycle_endpoints(auth_client):
    # 1. Create watcher
    create_resp = auth_client.post("/api/watchers", json={
        "target": "target-watcher-test.org",
        "target_type": "domain",
        "interval_minutes": 120,
    })
    assert create_resp.status_code == 200
    watcher_id = create_resp.json()["watcher"]["id"]

    # 2. List watchers
    list_resp = auth_client.get("/api/watchers")
    assert list_resp.status_code == 200
    assert any(w["id"] == watcher_id for w in list_resp.json()["watchers"])

    # 3. Delete watcher
    del_resp = auth_client.delete(f"/api/watchers/{watcher_id}")
    assert del_resp.status_code == 200

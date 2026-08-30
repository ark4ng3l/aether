"""
Tests for Next-Gen 5-Pillar AETHER Modules:
- StealthBrowserTool
- DarkWebReconTool
- WatchdogDaemon
- AttackMapper (MITRE ATT&CK Correlation)
- Direct Tool Execution & Threat Modeling Endpoints
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from aether.perception.tools.stealth_browser import StealthBrowserTool
from aether.perception.tools.darkweb_tools import DarkWebReconTool
from aether.reasoning.attack_mapper import AttackMapper
from aether.core.watchdog import WatchdogDaemon, GraphDelta
from aether.core.state import Entity, EntityType
from aether.core.project_manager import project_manager
from aether.api.server import app, AUTH_TOKEN


@pytest.mark.asyncio
async def test_stealth_browser_tool():
    tool = StealthBrowserTool()
    assert tool.name == "stealth_crawler"
    assert tool.category == "Web Forensics & Dynamic Scraping"

    # Test parameter validation
    res = await tool.execute()
    assert not res.success
    assert "Missing URL" in res.error

    # Test execution against mock/real URL
    res2 = await tool.execute(url="https://example.com", capture_screenshot=False)
    assert res2.success
    assert "example.com" in res2.data["target_url"]
    assert "title" in res2.data


@pytest.mark.asyncio
async def test_darkweb_recon_tool():
    tool = DarkWebReconTool()
    assert tool.name == "darkweb_recon"
    assert tool.category == "Threat & Dark Web Intelligence"

    # Test query validation
    res = await tool.execute()
    assert not res.success

    # Test execution
    res2 = await tool.execute(query="acme-corp.com", check_ransomware_leaks=False)
    assert res2.success
    assert "darknet_risk_level" in res2.data
    assert "onion_results" in res2.data


def test_mitre_attack_mapper():
    entities = [
        Entity(
            id="192.168.1.100",
            type=EntityType.IP_ADDRESS,
            confidence=0.9,
            properties={"ports": ["22/tcp", "80/tcp"], "banner": "Apache/2.4.41 OpenSSH_8.2p1"}
        ),
        Entity(
            id="CVE-2021-41773",
            type=EntityType.CVE,
            confidence=0.95,
            properties={"description": "Apache HTTP Server Path Traversal and RCE"}
        ),
        Entity(
            id="admin@target-corp.com",
            type=EntityType.EMAIL,
            confidence=0.85,
            properties={"breaches": ["Collection1", "ExploitIn"]}
        ),
    ]

    techniques = AttackMapper.analyze_entities(entities)
    assert len(techniques) >= 2

    tech_ids = [t["technique_id"] for t in techniques]
    assert "T1190" in tech_ids or "T1133" in tech_ids or "T1589" in tech_ids

    # Generate graph nodes
    nodes = AttackMapper.generate_attack_path_nodes(techniques, "target-corp.com")
    assert len(nodes) == len(techniques)
    assert "mitre_" in nodes[0].id


@pytest.mark.asyncio
async def test_watchdog_daemon():
    daemon = WatchdogDaemon()
    deltas = await daemon.run_all_checks()
    assert isinstance(deltas, list)

    delta = GraphDelta(
        project_id="proj_test",
        project_name="Test Project",
        target_seed="example.com",
        new_entities=[{"id": "sub.example.com", "type": "domain"}],
        new_threats=[],
        timestamp="2026-08-30T12:00:00Z"
    )
    assert delta.has_changes
    assert delta.to_dict()["new_entities_count"] == 1


@pytest.mark.asyncio
async def test_server_threat_modeling_and_direct_pivot():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

        # 1. Create a project
        create_res = await ac.post(
            "/api/projects",
            json={"target_seed": "threat-test.com", "target_type": "domain", "name": "Threat Test Project"},
            headers=headers
        )
        assert create_res.status_code == 200
        proj_id = create_res.json()["project"]["id"]

        # 2. Test MITRE Threat Model endpoint
        threat_res = await ac.post(
            f"/api/projects/{proj_id}/threat-model?inject_nodes=true",
            headers=headers
        )
        assert threat_res.status_code == 200
        assert "mitre_techniques" in threat_res.json()

        # 3. Test Direct Tool Execution endpoint
        pivot_res = await ac.post(
            f"/api/projects/{proj_id}/execute-tool-direct",
            json={
                "tool_name": "whois_lookup",
                "params": {"domain": "threat-test.com"},
                "reasoning": "Pivot from graph test",
            },
            headers=headers
        )
        assert pivot_res.status_code == 200
        assert pivot_res.json()["status"] == "completed"

        # 4. Test Watchdog Status endpoint
        wd_res = await ac.get("/api/watchdog/status", headers=headers)
        assert wd_res.status_code == 200
        assert "enabled" in wd_res.json()

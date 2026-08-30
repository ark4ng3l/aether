"""
Tests for OSINT Framework Complete Expansion Suite.
"""

import pytest
from aether.perception.tools.registry import registry
from aether.perception.tools.crypto_tools import CryptoTracerTool
from aether.perception.tools.transport_tools import GeoTransportTool
from aether.perception.tools.sanctions_tools import SanctionsScreenerTool
from aether.perception.tools.advanced_visual_tools import VisualForensicsSuiteTool
from aether.perception.tools.paste_tools import PasteHunterTool
from aether.perception.tools.reverse_whois_tools import ReverseWhoisTool


@pytest.mark.asyncio
async def test_crypto_tracer_tool():
    tool = CryptoTracerTool()
    # Test known ransomware address
    res = await tool.execute(address="14krLcmMGvTBRPdCH4Ahnz1oY46kP6w86x")
    assert res.success is True
    assert res.data["detected_chain"] == "BTC"
    assert "WannaCry" in res.data["risk_assessment"]
    assert res.data["risk_level"] == "CRITICAL"

    # Test clean EVM address
    res_eth = await tool.execute(address="0x0000000000000000000000000000000000000000")
    assert res_eth.success is True
    assert res_eth.data["detected_chain"] == "ETH"


@pytest.mark.asyncio
async def test_geo_transport_tool():
    tool = GeoTransportTool()
    # Test aviation lookup
    res_flight = await tool.execute(identifier="THY123", transport_type="aviation")
    assert res_flight.success is True
    assert res_flight.data["mode"] == "AVIATION (ADS-B Radar)"
    assert "flightradar24" in res_flight.data["radar_links"]

    # Test maritime lookup
    res_ship = await tool.execute(identifier="MMSI:244750000", transport_type="maritime")
    assert res_ship.success is True
    assert res_ship.data["mode"] == "MARITIME (AIS Marine Radar)"
    assert "marinetraffic" in res_ship.data["radar_portals"]


@pytest.mark.asyncio
async def test_sanctions_screener_tool():
    tool = SanctionsScreenerTool()
    res = await tool.execute(name="Test Entity")
    assert res.success is True
    assert "queried_name" in res.data
    assert "overall_risk_tier" in res.data


@pytest.mark.asyncio
async def test_visual_forensics_suite_tool():
    tool = VisualForensicsSuiteTool()
    res = await tool.execute(image_path_or_url="https://example.com/photo.jpg", shadow_object_ratio=1.2)
    assert res.success is True
    assert "reverse_image_search_engines" in res.data
    assert "sun_shadow_chronolocation" in res.data
    assert res.data["sun_shadow_chronolocation"]["calculated_sun_elevation_angle_deg"] > 0


@pytest.mark.asyncio
async def test_paste_hunter_tool():
    tool = PasteHunterTool()
    res = await tool.execute(query="target.corp")
    assert res.success is True
    assert "pastes" in res.data
    assert "dork_used" in res.data


@pytest.mark.asyncio
async def test_reverse_whois_tool():
    tool = ReverseWhoisTool()
    res = await tool.execute(identifier="example.com")
    assert res.success is True
    assert "discovered_domains" in res.data
    assert "reverse_whois_search_portals" in res.data


def test_registry_integration():
    """Verify all 6 tools are properly registered in the global tool registry."""
    tool_names = [t["name"] if isinstance(t, dict) else t.name for t in registry.list_tools()]
    assert "crypto_tracer" in tool_names
    assert "geo_transport_tracker" in tool_names
    assert "sanctions_pep_screener" in tool_names
    assert "visual_forensics_suite" in tool_names
    assert "paste_dump_hunter" in tool_names
    assert "reverse_whois_matrix" in tool_names

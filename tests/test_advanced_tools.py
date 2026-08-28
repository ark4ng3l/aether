"""
Unit tests for new Advanced OSINT Tools (Subdomains, GeoIP, Breaches) & STIX Export.
"""

import pytest
from unittest.mock import AsyncMock, patch

from aether.perception.tools.subdomain_tools import SubdomainFinderTool
from aether.perception.tools.geo_tools import IPGeoThreatTool
from aether.perception.tools.breach_tools import BreachCheckerTool
from aether.perception.tools.social_tools import SocialTools


@pytest.mark.asyncio
class TestAdvancedOSINTTools:
    async def test_subdomain_finder_basic(self):
        tool = SubdomainFinderTool()
        result = await tool.execute(domain="example.com")
        assert result.success is True
        assert "subdomains" in result.data
        assert result.data["domain"] == "example.com"
        assert len(result.data["subdomains"]) > 0

    async def test_ip_geolocate_basic(self):
        tool = IPGeoThreatTool()
        result = await tool.execute(ip="8.8.8.8")
        assert result.success is True
        assert "ip" in result.data
        assert "country" in result.data
        assert "lat" in result.data
        assert "lon" in result.data

    async def test_social_recon_broad(self):
        tool = SocialTools()
        perms = tool._generate_permutations("testuser")
        assert len(perms) >= 1
        assert "testuser" in perms

    async def test_breach_lookup(self):
        tool = BreachCheckerTool()
        result = await tool.execute(query="test_user")
        assert result.success is True
        assert "leaks" in result.data
        assert "breach_indicators_found" in result.data

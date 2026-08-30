"""
Unit tests for the 8 New Passive OSINT Tools:
- Wayback Machine CDX Lookup
- Favicon MurmurHash3 Fingerprinting
- Tech Stack Fingerprinting
- Typosquat & Phishing Detection
- ASN & BGP Network Lookup
- SSL/TLS Certificate Chain Inspection
- Cloud Storage Bucket Exposure Recon
- Robots.txt & Sitemap Recon
"""

import pytest
from aether.perception.tools.registry import registry
from aether.perception.tools.wayback_tools import wayback_tool
from aether.perception.tools.favicon_tools import favicon_tool, mmh3_32
from aether.perception.tools.tech_stack_tools import tech_stack_tool
from aether.perception.tools.typosquat_tools import typosquat_tool, generate_permutations
from aether.perception.tools.asn_tools import asn_tool
from aether.perception.tools.ssl_tools import ssl_tool
from aether.perception.tools.bucket_tools import bucket_tool
from aether.perception.tools.sitemap_tools import robots_sitemap_tool


class TestNewPassiveOSINTTools:
    """Validates registration and execution of all 8 advanced passive tools."""

    def test_tools_registered_in_global_registry(self):
        expected_tools = [
            "wayback_lookup",
            "favicon_fingerprint",
            "tech_stack_fingerprint",
            "typosquat_recon",
            "asn_lookup",
            "ssl_cert_inspector",
            "cloud_bucket_recon",
            "robots_sitemap_recon",
        ]
        registered_names = [t["name"] for t in registry.list_tools()]
        for tool_name in expected_tools:
            assert tool_name in registered_names, f"Tool '{tool_name}' should be in registry"

    @pytest.mark.asyncio
    async def test_wayback_tool_validation(self):
        # Empty input validation
        res_empty = await wayback_tool.execute()
        assert res_empty.success is False

        # Target lookup
        res = await wayback_tool.execute(domain="example.com", limit=5)
        assert isinstance(res.data, dict)
        assert "domain" in res.data

    def test_favicon_mmh3_pure_python_hash(self):
        # Test vector for known base64 bytes
        test_bytes = b"AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAA"
        h = mmh3_32(test_bytes)
        assert isinstance(h, int)

    @pytest.mark.asyncio
    async def test_favicon_tool_validation(self):
        res_empty = await favicon_tool.execute()
        assert res_empty.success is False

    @pytest.mark.asyncio
    async def test_tech_stack_tool_validation(self):
        res_empty = await tech_stack_tool.execute()
        assert res_empty.success is False

        res = await tech_stack_tool.execute(url="https://example.com")
        assert isinstance(res.data, dict)

    def test_typosquat_permutation_generator(self):
        perms = generate_permutations("google.com")
        assert len(perms) > 0
        domains = [p[0] for p in perms]
        # Should contain omissions, substitutions, or tld swaps
        assert any(d.endswith(".org") or d.endswith(".net") or "0" in d for d in domains)

    @pytest.mark.asyncio
    async def test_typosquat_tool_validation(self):
        res_empty = await typosquat_tool.execute()
        assert res_empty.success is False

        res = await typosquat_tool.execute(domain="google.com", max_checks=3)
        assert res.success is True
        assert "generated_candidates_checked" in res.data

    @pytest.mark.asyncio
    async def test_asn_tool_validation(self):
        res_empty = await asn_tool.execute()
        assert res_empty.success is False

        res = await asn_tool.execute(asn_or_ip="AS15169")
        assert isinstance(res.data, dict)

    @pytest.mark.asyncio
    async def test_ssl_tool_validation(self):
        res_empty = await ssl_tool.execute()
        assert res_empty.success is False

    @pytest.mark.asyncio
    async def test_cloud_bucket_tool_validation(self):
        res_empty = await bucket_tool.execute()
        assert res_empty.success is False

        res = await bucket_tool.execute(brand_name="google")
        assert res.success is True
        assert res.data["probes_executed"] > 0
        assert "discovered_buckets" in res.data

    @pytest.mark.asyncio
    async def test_robots_sitemap_tool_validation(self):
        res_empty = await robots_sitemap_tool.execute()
        assert res_empty.success is False

        res = await robots_sitemap_tool.execute(domain="example.com")
        assert res.success is True
        assert "disallow_paths" in res.data

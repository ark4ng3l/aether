"""
Unit tests for the 7 new OSINT & Active Reconnaissance tools.
"""

import pytest
from aether.perception.tools.passive_dns_tools import passive_dns_tool
from aether.perception.tools.email_security_tools import email_security_tool
from aether.perception.tools.certstream_tools import cert_transparency_tool
from aether.perception.tools.threat_reputation_tools import threat_reputation_tool
from aether.perception.tools.port_prober_tools import port_prober_tool
from aether.perception.tools.security_headers_tools import security_headers_tool
from aether.perception.tools.api_schema_tools import api_schema_tool


@pytest.mark.asyncio
async def test_passive_dns_tool():
    res = await passive_dns_tool.execute(domain="example.com")
    assert res.success is True
    assert "target" in res.data
    assert "resolution_history" in res.data


@pytest.mark.asyncio
async def test_email_security_tool():
    res = await email_security_tool.execute(domain="google.com")
    assert res.success is True
    assert "spf" in res.data
    assert "dmarc" in res.data
    assert "security_assessment" in res.data


@pytest.mark.asyncio
async def test_cert_transparency_tool():
    res = await cert_transparency_tool.execute(domain="example.com")
    assert res.success is True
    assert "subdomains" in res.data


@pytest.mark.asyncio
async def test_threat_reputation_tool():
    res = await threat_reputation_tool.execute(indicator="1.1.1.1")
    assert res.success is True
    assert "is_malicious" in res.data
    assert "threat_level" in res.data


@pytest.mark.asyncio
async def test_port_prober_tool():
    # Probe localhost on port 8000 (which may be open or closed, but must not crash)
    res = await port_prober_tool.execute(host="127.0.0.1", ports=[8000, 9999])
    assert res.success is True
    assert "scanned_ports_count" in res.data
    assert res.data["scanned_ports_count"] == 2


@pytest.mark.asyncio
async def test_security_headers_tool():
    res = await security_headers_tool.execute(url="https://example.com")
    # Even if network is simulated or live, it returns structured result
    assert isinstance(res.data, dict)


@pytest.mark.asyncio
async def test_api_schema_tool():
    res = await api_schema_tool.execute(url="https://example.com")
    assert res.success is True
    assert "openapi_schemas" in res.data
    assert "graphql_schemas" in res.data

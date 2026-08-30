"""
Tests for SSLCertInspectorTool.
"""

import pytest
from unittest.mock import patch, MagicMock
from aether.perception.tools.ssl_tools import ssl_tool


@pytest.mark.asyncio
async def test_ssl_cert_inspector_mocked():
    """Validates certificate parsing against mocked SSL socket."""
    mock_cert = {
        "subject": ((("commonName", "example.com"),),),
        "issuer": ((("organizationName", "DigiCert Inc"),), (("commonName", "DigiCert Global Root CA"),)),
        "version": 3,
        "serialNumber": "0F1234567890ABCDEF",
        "notBefore": "Jan  1 00:00:00 2025 GMT",
        "notAfter": "Jan  1 00:00:00 2026 GMT",
        "subjectAltName": (("DNS", "example.com"), ("DNS", "www.example.com")),
    }

    mock_sock = MagicMock()
    mock_sock.getpeercert.return_value = mock_cert

    with patch("ssl.create_default_context") as mock_ctx:
        ctx_inst = MagicMock()
        ctx_inst.wrap_socket.return_value.__enter__.return_value = mock_sock
        mock_ctx.return_value = ctx_inst
        with patch("socket.create_connection", return_value=MagicMock()):
            res = await ssl_tool.execute(domain="example.com")
            assert res.success is True
            assert "example.com" in str(res.data)

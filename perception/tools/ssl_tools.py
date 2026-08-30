"""
SSL/TLS Certificate Chain & SAN Analyzer Tool.
Performs passive TLS handshakes to extract certificate authority, SAN subdomains, and expiration telemetry.
"""

from __future__ import annotations

import asyncio
import datetime
import socket
import ssl
from typing import Any, Dict, List, Optional, Tuple

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class SslCertInspectorTool(BaseTool):
    """Passively analyzes SSL/TLS certificate chains, SAN subdomains, and expiration dates."""

    def __init__(self):
        super().__init__(
            name="ssl_cert_inspector",
            description="Inspects SSL/TLS certificate metadata, issuer authority, Subject Alternative Names (SAN subdomains), cipher suites, and expiration telemetry.",
            category="OSINT",
            icon="ShieldCheck",
            default_param_key="hostname",
            example_input="google.com",
            params={
                "hostname": "Target hostname or domain name (e.g. google.com)",
                "port": "HTTPS port (default: 443)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        host = kwargs.get("hostname") or kwargs.get("domain") or kwargs.get("query") or ""
        host = str(host).strip().lower()
        if host.startswith("http://") or host.startswith("https://"):
            host = host.split("://")[1].split("/")[0]

        try:
            port = int(kwargs.get("port") or 443)
        except (ValueError, TypeError):
            port = 443

        # Perform TLS handshake inside executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        try:
            cert_data = await loop.run_in_executor(None, self._get_certificate, host, port)
            return ToolResult(success=True, data=cert_data)
        except Exception as exc:
            logger.warning(f"SSL certificate inspection failed for {host}:{port}: {exc}")
            return ToolResult(success=False, data={"hostname": host, "port": port}, error=str(exc))

    def _get_certificate(self, host: str, port: int) -> Dict[str, Any]:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=8.0) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                cipher = ssock.cipher()
                version = ssock.version()

                # If binary form is needed because verify_mode=CERT_NONE returned empty dict
                if not cert:
                    # Retry with normal verify context
                    try:
                        ctx_strict = ssl.create_default_context()
                        with socket.create_connection((host, port), timeout=8.0) as sock2:
                            with ctx_strict.wrap_socket(sock2, server_hostname=host) as ssock2:
                                cert = ssock2.getpeercert()
                    except Exception:
                        pass

                subject_dict = {}
                issuer_dict = {}
                san_list = []

                if cert:
                    for item in cert.get("subject", []):
                        for k, v in item:
                            subject_dict[k] = v

                    for item in cert.get("issuer", []):
                        for k, v in item:
                            issuer_dict[k] = v

                    for typ, val in cert.get("subjectAltName", []):
                        if typ == "DNS":
                            san_list.append(val)

                    not_after = cert.get("notAfter")
                    not_before = cert.get("notBefore")

                    days_left = None
                    is_expired = False

                    if not_after:
                        try:
                            # Format: 'May 22 23:59:59 2024 GMT'
                            expire_dt = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=datetime.timezone.utc)
                            now = datetime.datetime.now(datetime.timezone.utc)
                            diff = expire_dt - now
                            days_left = diff.days
                            is_expired = days_left < 0
                        except Exception:
                            pass

                    return {
                        "hostname": host,
                        "port": port,
                        "tls_version": version,
                        "cipher_suite": cipher[0] if cipher else "Unknown",
                        "subject_common_name": subject_dict.get("commonName"),
                        "subject_organization": subject_dict.get("organizationName"),
                        "issuer_common_name": issuer_dict.get("commonName"),
                        "issuer_organization": issuer_dict.get("organizationName"),
                        "valid_from": not_before,
                        "valid_until": not_after,
                        "days_remaining": days_left,
                        "is_expired": is_expired,
                        "san_count": len(san_list),
                        "subject_alt_names": san_list,
                        "san_subdomains_discovered": [s for s in san_list if s != host and not s.startswith("*")],
                    }

                return {
                    "hostname": host,
                    "port": port,
                    "tls_version": version,
                    "cipher_suite": cipher[0] if cipher else "Unknown",
                    "message": "TLS connection established, but certificate details are unparsed.",
                }


ssl_tool = SslCertInspectorTool()

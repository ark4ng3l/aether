"""
Async Port & Service Prober Tool for AETHER.
Performs fast, non-destructive TCP connectivity checks and banner grabbing on standard critical service ports.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Any, Dict, List
from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger

DEFAULT_CRITICAL_PORTS = {
    21: "FTP",
    22: "SSH",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    1433: "MSSQL",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    6379: "Redis",
    8080: "HTTP-Alt / Proxy",
    8443: "HTTPS-Alt",
    9200: "Elasticsearch",
    27017: "MongoDB",
}


class PortProberTool(BaseTool):
    """Fast async port scanner and service banner grabber for defensive network mapping."""

    def __init__(self):
        super().__init__(
            name="port_prober",
            description="Performs non-destructive async TCP port probing and service banner grabbing on critical ports (SSH, Web, Databases, Remote Access).",
            category="Recon",
            icon="Radio",
            default_param_key="host",
            example_input="1.1.1.1",
            params={
                "host": "Target hostname or IP address (e.g. example.com or 192.168.1.1)",
                "ports": "Optional comma-separated list of ports (default: critical ports suite)",
            },
        )

    async def execute(self, **kwargs) -> ToolResult:
        host = kwargs.get("host") or kwargs.get("hostname") or kwargs.get("domain") or kwargs.get("query") or ""
        host = str(host).strip()
        if host.startswith(("http://", "https://")):
            host = host.split("://")[1].split("/")[0]
        if ":" in host and not host.count(":") > 1: # IPv4 with port
            host = host.split(":")[0]

        if not host:
            return ToolResult(success=False, data={}, error="Host/IP required for port probe.")

        ports_raw = kwargs.get("ports")
        if ports_raw:
            try:
                if isinstance(ports_raw, list):
                    target_ports = [int(p) for p in ports_raw]
                else:
                    target_ports = [int(p.strip()) for p in str(ports_raw).split(",") if p.strip().isdigit()]
            except Exception:
                target_ports = list(DEFAULT_CRITICAL_PORTS.keys())
        else:
            target_ports = list(DEFAULT_CRITICAL_PORTS.keys())

        logger.info(f"Probing {len(target_ports)} critical ports on host: {host}")

        open_ports: List[Dict[str, Any]] = []
        tasks = [self._probe_single_port(host, port) for port in target_ports]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, dict) and res.get("status") == "open":
                open_ports.append(res)

        return ToolResult(
            success=True,
            data={
                "host": host,
                "scanned_ports_count": len(target_ports),
                "open_ports_count": len(open_ports),
                "open_ports": sorted(open_ports, key=lambda x: x["port"]),
                "summary": f"Discovered {len(open_ports)} open service ports on {host}.",
            },
        )

    async def _probe_single_port(self, host: str, port: int) -> Dict[str, Any]:
        service_name = DEFAULT_CRITICAL_PORTS.get(port, f"Custom-{port}")
        loop = asyncio.get_event_loop()

        def _sync_connect():
            banner = ""
            try:
                with socket.create_connection((host, port), timeout=2.5) as s:
                    s.settimeout(1.5)
                    try:
                        # Attempt to receive initial banner if service sends greeting
                        raw = s.recv(1024)
                        banner = raw.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        banner = ""
                return {"port": port, "service": service_name, "status": "open", "banner": banner}
            except (socket.timeout, ConnectionRefusedError, OSError):
                return {"port": port, "service": service_name, "status": "closed", "banner": ""}

        try:
            return await loop.run_in_executor(None, _sync_connect)
        except Exception:
            return {"port": port, "service": service_name, "status": "closed", "banner": ""}


port_prober_tool = PortProberTool()

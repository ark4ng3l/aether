"""
GeoTools — IP Geolocation, ASN, and Threat Infrastructure Mapping.

Queries IP metadata and geocodes coordinates for Geo-OSINT visualization.
"""

from __future__ import annotations

import re
import socket
from typing import Dict, Any

import httpx

from aether.perception.tools.registry import BaseTool, ToolResult
from aether.core.logger import logger


class IPGeoThreatTool(BaseTool):
    """Resolves geolocation, ISP, ASN, and coordinates for an IP address."""

    def __init__(self):
        super().__init__(
            name="ip_geolocate",
            description="Extracts country, city, coordinates (lat/lon), ISP, and ASN for an IP address.",
            category="Geo-OSINT & Infrastructure",
            icon="public",
            default_param_key="ip",
            example_input="1.1.1.1",
        )

    async def execute(self, ip: str = "", **kwargs) -> ToolResult:
        target_ip = ip or kwargs.get("query", "")
        if not target_ip:
            return ToolResult(success=False, data={}, error="No IP address provided")

        # Basic IP clean
        target_ip = target_ip.strip()

        # If domain passed instead, try to resolve to IP first
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target_ip):
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                target_ip = await loop.run_in_executor(None, socket.gethostbyname, target_ip)
            except Exception:
                pass

        logger.info(f"Geolocating IP: {target_ip}")
        data: Dict[str, Any] = {
            "ip": target_ip,
            "country": "Unknown",
            "city": "Unknown",
            "region": "Unknown",
            "lat": 0.0,
            "lon": 0.0,
            "isp": "Unknown",
            "asn": "Unknown",
            "reverse_dns": "Unknown",
        }

        # Reverse DNS lookup
        try:
            hostname, _, _ = socket.gethostbyaddr(target_ip)
            data["reverse_dns"] = hostname
        except Exception:
            pass

        # Query ip-api.com
        try:
            url = f"http://ip-api.com/json/{target_ip}?fields=status,message,country,countryCode,regionName,city,lat,lon,timezone,isp,org,as,query"
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    api_data = resp.json()
                    if api_data.get("status") == "success":
                        data["country"] = api_data.get("country", "Unknown")
                        data["country_code"] = api_data.get("countryCode", "")
                        data["region"] = api_data.get("regionName", "Unknown")
                        data["city"] = api_data.get("city", "Unknown")
                        data["lat"] = float(api_data.get("lat", 0.0))
                        data["lon"] = float(api_data.get("lon", 0.0))
                        data["timezone"] = api_data.get("timezone", "")
                        data["isp"] = api_data.get("isp", "Unknown")
                        data["org"] = api_data.get("org", "Unknown")
                        data["asn"] = api_data.get("as", "Unknown")
        except Exception as exc:
            logger.warning(f"GeoIP resolution failed for {target_ip}: {exc}")

        return ToolResult(success=True, data=data)


geo_tools = IPGeoThreatTool()

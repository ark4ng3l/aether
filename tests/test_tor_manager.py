"""
Tests for aether.core.tor_manager and Tor integration endpoints in aether.api.server.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from aether.core.tor_manager import TorManager, tor_manager
from aether.api.server import app
import aether.api.server as server_module


@pytest.fixture
def client():
    return TestClient(app, headers={"Authorization": f"Bearer {server_module.AUTH_TOKEN}"})


class TestTorManager:
    def test_tor_manager_initial_state(self):
        manager = TorManager(socks_port=9050, control_port=9051)
        assert manager.socks_port == 9050
        assert manager.control_port == 9051
        assert "socks5://127.0.0.1:9050" == manager.socks_proxy_url

    def test_tor_status_structure(self):
        status = tor_manager.get_status()
        assert "installed" in status
        assert "running" in status
        assert "bootstrapped" in status
        assert "bootstrap_progress_pct" in status
        assert "socks_proxy_url" in status
        assert status["socks_port"] == 9050

    @pytest.mark.asyncio
    async def test_tor_mocked_start_and_stop(self):
        manager = TorManager(socks_port=9998, control_port=9999)
        with patch.object(manager, "_is_port_listening", return_value=True):
            ok = await manager.start()
            assert ok is True
            assert manager.is_bootstrapped is True
            assert manager.bootstrap_progress == 100

        await manager.stop()
        assert manager.is_bootstrapped is False
        assert manager.bootstrap_progress == 0


class TestTorServerEndpoints:
    def test_get_tor_status_endpoint(self, client: TestClient):
        resp = client.get("/api/tor/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "installed" in data
        assert "running" in data
        assert "socks_proxy_url" in data

    def test_tor_in_health_diagnostics(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "diagnostics" in data
        assert "tor_status" in data["diagnostics"]
        assert "socks_proxy_url" in data["diagnostics"]["tor_status"]

    @pytest.mark.asyncio
    async def test_get_tor_exit_ip_endpoint(self, client: TestClient):
        with patch("aether.core.tor_manager.tor_manager.get_exit_ip", new_callable=AsyncMock) as mock_ip:
            mock_ip.return_value = {"tor_active": True, "ip": "185.220.101.103", "cached": False}
            resp = client.get("/api/tor/exit-ip")
            assert resp.status_code == 200
            assert resp.json()["tor_active"] is True
            assert resp.json()["ip"] == "185.220.101.103"

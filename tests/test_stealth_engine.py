"""
Tests for aether.core.stealth_engine and Stealth endpoints in aether.api.server.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from aether.core.stealth_engine import StealthEngine, stealth_engine
from aether.api.server import app
import aether.api.server as server_module


@pytest.fixture
def client():
    return TestClient(app, headers={"Authorization": f"Bearer {server_module.AUTH_TOKEN}"})


class TestStealthEngine:
    def test_persona_generation(self):
        engine = StealthEngine()
        persona = engine.generate_persona()
        assert persona.os_name in ["Windows", "macOS", "Linux"]
        assert persona.browser_name in ["Chrome", "Firefox"]
        assert len(persona.user_agent) > 20
        assert persona.screen_width >= 1200
        assert persona.screen_height >= 700
        assert persona.device_memory_gb in [8, 16, 32]

    def test_playwright_stealth_script(self):
        engine = StealthEngine()
        script = engine.get_playwright_stealth_init_script()
        assert "webdriver" in script
        assert "RTCPeerConnection" in script  # WebRTC leak blocker
        assert "toDataURL" in script  # Canvas noise
        assert "AudioBuffer" in script  # Audio noise
        assert "makeNative" in script  # Native function masking
        assert "UNMASKED_RENDERER_WEBGL" in script  # GPU hardware spoofing
        assert "getTimezoneOffset" in script  # Timezone alignment

    def test_proxy_pool_and_strategies(self):
        engine = StealthEngine()
        engine._proxy_pool = []
        engine.set_proxy_strategy("DIRECT")
        assert engine.get_active_proxy() is None

        engine.add_proxies(["socks5://10.0.0.1:1080", "http://10.0.0.2:8080"])
        engine.set_proxy_strategy("ROTATING_POOL")
        p1 = engine.get_active_proxy()
        p2 = engine.get_active_proxy()
        assert p1 in ["socks5://10.0.0.1:1080", "http://10.0.0.2:8080"]
        assert p2 in ["socks5://10.0.0.1:1080", "http://10.0.0.2:8080"]


class TestStealthServerEndpoints:
    def test_get_stealth_status(self, client: TestClient):
        resp = client.get("/api/stealth/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_persona" in data
        assert "anti_fingerprinting_suite" in data
        assert "proxy_strategy" in data

    def test_rotate_persona_endpoint(self, client: TestClient):
        resp = client.post("/api/stealth/rotate-persona")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rotated"
        assert "persona" in data
        assert "os_name" in data["persona"]

    def test_configure_proxies_endpoint(self, client: TestClient):
        resp = client.post("/api/stealth/proxies", json={
            "strategy": "DIRECT",
            "proxies": ["socks5://127.0.0.1:9050"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["proxy_strategy"] == "DIRECT"

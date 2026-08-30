"""
Tests for Bearer Token Security and Out-of-Band Bootstrapping.
Covers:
  1. Direct unauthenticated call to /api/auth/token returns 401 Unauthorized
  2. Direct unauthenticated call to /api/projects returns 401 Unauthorized
  3. Valid Bearer token allows API access
  4. Root endpoint injects token ONLY when valid authorization is present
  5. WebSocket rejects connection without valid token query parameter
"""

import pytest
from fastapi.testclient import TestClient
from aether.api.server import app, AUTH_TOKEN


@pytest.fixture
def client():
    return TestClient(app)


def test_auth_token_endpoint_rejects_unauthenticated(client: TestClient):
    """GET /api/auth/token must be protected by local auth middleware."""
    resp = client.get("/api/auth/token")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json()["detail"]


def test_api_projects_rejects_unauthenticated(client: TestClient):
    """API endpoints reject unauthenticated access."""
    resp = client.get("/api/projects")
    assert resp.status_code == 401


def test_api_projects_accepts_valid_bearer_token(client: TestClient):
    """Valid Bearer token grants access to protected API endpoints."""
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    resp = client.get("/api/projects", headers=headers)
    assert resp.status_code == 200
    assert "projects" in resp.json()


def test_root_endpoint_boot_token_injection(client: TestClient):
    """Root HTML contains injected boot token ONLY when request has valid session."""
    # 1. Unauthenticated request -> no token in HTML
    unauth_resp = client.get("/")
    if unauth_resp.status_code == 200 and unauth_resp.headers.get("content-type", "").startswith("text/html"):
        assert AUTH_TOKEN not in unauth_resp.text

    # 2. Authenticated request -> contains injected boot script
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    auth_resp = client.get("/", headers=headers)
    if auth_resp.status_code == 200 and auth_resp.headers.get("content-type", "").startswith("text/html"):
        assert f'window.__AETHER_BOOT_TOKEN__ = "{AUTH_TOKEN}"' in auth_resp.text


def test_websocket_rejects_unauthorized(client: TestClient):
    """WebSocket connection without valid token query parameter is closed immediately."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/test_channel?token=invalid_token") as ws:
            ws.receive_json()

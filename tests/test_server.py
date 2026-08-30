"""Tests for aether.api.server — FastAPI project management endpoints and security."""

from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from aether.api.server import app, AUTH_TOKEN
from aether.core.project_manager import ProjectManager
import aether.api.server as server_module
import aether.core.project_manager as pm_module


@pytest.fixture(autouse=True)
def isolate_project_manager(tmp_path: Path, monkeypatch):
    """Isolate project_manager storage into a temporary directory during tests."""
    temp_pm = ProjectManager(data_dir=str(tmp_path / "data"))
    monkeypatch.setattr(server_module, "project_manager", temp_pm)
    monkeypatch.setattr(pm_module, "project_manager", temp_pm)
    return temp_pm


@pytest.fixture
def client():
    return TestClient(app, headers={"Authorization": f"Bearer {AUTH_TOKEN}"})


@pytest.fixture
def unauth_client():
    return TestClient(app)


class TestHealthAndAuthEndpoints:
    def test_health_public(self, unauth_client: TestClient):
        resp = unauth_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["engine"] == "AETHER"

    def test_auth_token_protected(self, client: TestClient, unauth_client: TestClient):
        # Unauthenticated request without token header is rejected with 401
        resp_unauth = unauth_client.get("/api/auth/token")
        assert resp_unauth.status_code == 401

        # Authenticated request returns token
        resp_auth = client.get("/api/auth/token")
        assert resp_auth.status_code == 200
        assert resp_auth.json()["token"] == AUTH_TOKEN

    def test_unauthenticated_request_rejected(self, unauth_client: TestClient):
        resp = unauth_client.get("/api/projects")
        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["detail"]

    def test_authenticated_request_with_query_param(self, unauth_client: TestClient):
        resp = unauth_client.get(f"/api/projects?token={AUTH_TOKEN}")
        assert resp.status_code == 200

    def test_root_injects_bootstrap_token_only_when_authenticated(self, client: TestClient, unauth_client: TestClient):
        resp_unauth = unauth_client.get("/")
        assert resp_unauth.status_code == 200
        if "text/html" in resp_unauth.headers.get("content-type", ""):
            assert AUTH_TOKEN not in resp_unauth.text

        resp_auth = client.get("/")
        assert resp_auth.status_code == 200
        if "text/html" in resp_auth.headers.get("content-type", ""):
            assert "__AETHER_BOOTSTRAP__" in resp_auth.text


class TestProjectEndpoints:
    def test_create_and_get_project(self, client: TestClient, isolate_project_manager: ProjectManager):
        resp = client.post(
            "/api/projects",
            json={
                "name": "API Test Project",
                "target_seed": "@apt_test",
                "target_type": "social_handle",
                "context_briefing": "Test intelligence briefing notes",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        proj = data["project"]
        assert proj["name"] == "API Test Project"
        assert proj["target_seed"] == "@apt_test"
        assert proj["context_briefing"] == "Test intelligence briefing notes"
        project_id = proj["id"]

        # Fetch it back
        get_resp = client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["project"]["id"] == project_id

    def test_list_projects(self, client: TestClient, isolate_project_manager: ProjectManager):
        isolate_project_manager.create_project(name="P1", target_seed="seed1.com")
        isolate_project_manager.create_project(name="P2", target_seed="seed2.com")

        resp = client.get("/api/projects")
        assert resp.status_code == 200
        projects = resp.json()["projects"]
        assert len(projects) == 2

    def test_update_project(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Old Name", target_seed="seed.com")
        resp = client.patch(
            f"/api/projects/{p.id}",
            json={"name": "New Name", "context_briefing": "Updated briefing"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["name"] == "New Name"
        assert data["project"]["context_briefing"] == "Updated briefing"

    def test_delete_project(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="To Delete", target_seed="del.com")
        resp = client.delete(f"/api/projects/{p.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        get_resp = client.get(f"/api/projects/{p.id}")
        assert get_resp.status_code == 404

    def test_run_project(self, client: TestClient, isolate_project_manager: ProjectManager, monkeypatch):
        p = isolate_project_manager.create_project(name="Run Test", target_seed="run.com")
        monkeypatch.setattr(isolate_project_manager, "run_project", AsyncMock(return_value=True))

        resp = client.post(f"/api/projects/{p.id}/run")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"

    def test_stop_project(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Stop Test", target_seed="stop.com")
        resp = client.post(f"/api/projects/{p.id}/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("stopped", "not_running")

    def test_project_tasks_endpoint(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Tasks Test", target_seed="tasks.com")
        resp = client.get(f"/api/projects/{p.id}/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == p.id
        assert "completed_tasks" in data

    def test_project_graph_endpoint(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Graph Test", target_seed="graph.com")
        resp = client.get(f"/api/projects/{p.id}/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    def test_project_dossier_endpoint(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Dossier Test", target_seed="dossier.com")
        resp = client.get(f"/api/projects/{p.id}/dossier")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == p.id
        assert "dossier" in data

    def test_settings_endpoints(self, client: TestClient):
        get_resp = client.get("/api/settings")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert "settings" in data

        post_resp = client.post("/api/settings", json={"MAX_SEARCH_DEPTH": 8})
        assert post_resp.status_code == 200
        assert post_resp.json()["status"] == "updated"

    def test_stix_and_timeline_endpoints(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Threat Export Test", target_seed="threat.org")
        
        # 1. Timeline
        timeline_resp = client.get(f"/api/projects/{p.id}/timeline")
        assert timeline_resp.status_code == 200
        tdata = timeline_resp.json()
        assert tdata["project_id"] == p.id
        assert len(tdata["events"]) >= 1

        # 2. STIX 2.1
        stix_resp = client.get(f"/api/projects/{p.id}/export/stix")
        assert stix_resp.status_code == 200
        sdata = stix_resp.json()
        assert sdata["type"] == "bundle"
        assert sdata["spec_version"] == "2.1"
        assert len(sdata["objects"]) >= 1
        assert sdata["objects"][0]["type"] == "identity"

    def test_system_update_check_endpoint(self, client: TestClient):
        resp = client.get("/api/system/update-check")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_version" in data
        assert "current_commit" in data

    def test_metrics_endpoint(self, client: TestClient):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_seconds" in data
        assert "investigations" in data
        assert "tools" in data
        assert "resource_arbiter" in data

    def test_image_upload_and_sanitization(self, client: TestClient):
        file_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00"
        files = {"file": ("test_pic.jpg", file_content, "image/jpeg")}
        resp = client.post("/api/upload/image", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "uploaded"
        filename = data["filename"]

        # Valid fetch
        img_resp = client.get(f"/api/images/{filename}")
        assert img_resp.status_code == 200

        # Path traversal attack attempt rejected
        evil_resp = client.get("/api/images/..%2F..%2Fpasswords.txt")
        assert evil_resp.status_code in (400, 404)

    def test_list_tools_endpoint(self, client: TestClient):
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert len(data["tools"]) >= 10
        tool_names = [t["name"] for t in data["tools"]]
        assert "web_search" in tool_names
        assert "company_recon" in tool_names
        assert "news_intel" in tool_names
        assert "threat_intel" in tool_names

    def test_execute_tool_live_endpoint(self, client: TestClient):
        payload = {
            "tool_name": "ip_geolocate",
            "params": {"ip": "1.1.1.1"}
        }
        resp = client.post("/api/tools/execute", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_name"] == "ip_geolocate"
        assert "execution_time_ms" in data
        assert "success" in data

    def test_token_regeneration(self, client: TestClient):
        old_token = server_module.AUTH_TOKEN
        try:
            resp = client.post("/api/auth/token/regenerate")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "regenerated"
            assert "token" in data
            assert len(data["token"]) == 48
        finally:
            server_module.AUTH_TOKEN = old_token
            server_module.AUTH_TOKEN_FILE.write_text(old_token, encoding="utf-8")

    def test_entity_provenance_endpoint(self, client: TestClient, isolate_project_manager: ProjectManager):
        proj = isolate_project_manager.create_project(name="Provenance Test", target_seed="example.com")
        resp = client.get(f"/api/projects/{proj.id}/entities/subdomain_finder_123/provenance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == proj.id
        assert data["entity_id"] == "subdomain_finder_123"
        assert "provenance_tasks" in data

    def test_dossier_export_consolidated(self, client: TestClient, isolate_project_manager: ProjectManager):
        proj = isolate_project_manager.create_project(name="Export Test", target_seed="target.org")
        proj.dossier = "# Intelligence Dossier\n\nTarget confirmed."
        isolate_project_manager._save_to_disk()

        # JSON format
        resp_json = client.get(f"/api/projects/{proj.id}/dossier/export?format=json")
        assert resp_json.status_code == 200
        assert resp_json.json()["target_seed"] == "target.org"

        # Markdown format
        resp_md = client.get(f"/api/projects/{proj.id}/dossier/export?format=md")
        assert resp_md.status_code == 200
        assert b"Intelligence Dossier" in resp_md.content

        # PDF/HTML format
        resp_pdf = client.get(f"/api/projects/{proj.id}/dossier/export?format=pdf")
        assert resp_pdf.status_code == 200
        assert b"<html>" in resp_pdf.content

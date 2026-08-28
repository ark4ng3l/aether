"""Tests for aether.api.server — FastAPI project management endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from aether.api.server import app
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
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["engine"] == "AETHER"

    def test_root_returns_html_or_json(self, client: TestClient):
        resp = client.get("/")
        assert resp.status_code == 200


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

        # Get project
        get_resp = client.get(f"/api/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["project"]["id"] == project_id

    def test_list_projects(self, client: TestClient, isolate_project_manager: ProjectManager):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_update_project(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="To Update", target_seed="update.com")
        resp = client.patch(
            f"/api/projects/{p.id}",
            json={"name": "Updated Name", "context_briefing": "Updated notes"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project"]["name"] == "Updated Name"
        assert data["project"]["context_briefing"] == "Updated notes"

    def test_delete_project(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="To Delete", target_seed="del.com")
        resp = client.delete(f"/api/projects/{p.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify not found
        get_resp = client.get(f"/api/projects/{p.id}")
        assert get_resp.status_code == 404

    def test_run_project(self, client: TestClient, isolate_project_manager: ProjectManager, monkeypatch):
        mock_run = AsyncMock(return_value=True)
        monkeypatch.setattr(isolate_project_manager, "run_project", mock_run)
        p = isolate_project_manager.create_project(name="Run Test", target_seed="run.com")
        resp = client.post(f"/api/projects/{p.id}/run")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"

    def test_stop_project(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Stop Test", target_seed="stop.com")
        resp = client.post(f"/api/projects/{p.id}/stop")
        assert resp.status_code == 200

    def test_project_tasks_endpoint(self, client: TestClient, isolate_project_manager: ProjectManager):
        p = isolate_project_manager.create_project(name="Task Test", target_seed="task.com")
        resp = client.get(f"/api/projects/{p.id}/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == p.id
        assert "completed_tasks" in data
        assert "pending_tasks" in data

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
        # 1. GET settings
        get_resp = client.get("/api/settings")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert "settings" in data
        assert "available_models" in data
        assert "HYPOTHESIS_RECURSION_LIMIT" in data["settings"]

        # 2. POST settings
        post_resp = client.post(
            "/api/settings",
            json={
                "HYPOTHESIS_RECURSION_LIMIT": 7,
                "MAX_SEARCH_DEPTH": 15,
                "REASONING_TEMPERATURE": 0.8,
            },
        )
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
        assert "repo_url" in data
        assert "update_available" in data

    def test_image_upload_endpoint(self, client: TestClient):
        file_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00"
        files = {"file": ("test_pic.jpg", file_content, "image/jpeg")}
        resp = client.post("/api/upload/image", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "uploaded"
        assert "filename" in data
        assert "file_path" in data

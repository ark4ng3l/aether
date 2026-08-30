"""
Tests for SQLite-first Project Persistence and One-time JSON Migration.
Covers:
  1. Fresh install (no JSON, empty DB) -> starts clean
  2. Legacy install (JSON present, empty DB) -> migrates and creates .migrated backup
  3. Already-migrated install (DB populated) -> does not re-run migration or touch JSON
"""

import json
import pytest
from pathlib import Path
from aether.core.project_manager import ProjectManager
from aether.core.state import Project, EntityType, InvestigationStatus


def test_fresh_install_starts_clean(tmp_path: Path):
    """A clean environment without projects.json starts with 0 projects."""
    mgr = ProjectManager(data_dir=str(tmp_path))
    assert len(mgr.list_projects()) == 0
    assert not (tmp_path / "projects.json").exists()
    assert not (tmp_path / "projects.json.migrated").exists()


def test_legacy_install_migrates_to_sqlite(tmp_path: Path):
    """When projects.json exists with an empty SQLite DB, migration runs and creates .migrated backup."""
    legacy_json = tmp_path / "projects.json"
    legacy_data = [
        {
            "id": "proj_mig_1",
            "name": "Legacy Project Alpha",
            "target_seed": "alpha.example.com",
            "target_type": "domain",
            "context_briefing": "Historical threat report",
            "status": "idle",
            "entities_count": 0,
            "completed_tasks_count": 0,
            "has_dossier": False,
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
        },
        {
            "id": "proj_mig_2",
            "name": "Legacy Project Beta",
            "target_seed": "192.168.1.1",
            "target_type": "ip_address",
            "context_briefing": "",
            "status": "idle",
            "entities_count": 0,
            "completed_tasks_count": 0,
            "has_dossier": False,
            "created_at": "2026-08-02T00:00:00Z",
            "updated_at": "2026-08-02T00:00:00Z",
        },
    ]
    legacy_json.write_text(json.dumps(legacy_data), encoding="utf-8")

    mgr = ProjectManager(data_dir=str(tmp_path))

    # Assert projects were loaded into memory from SQLite
    assert len(mgr.list_projects()) == 2
    p1 = mgr.get_project("proj_mig_1")
    assert p1 is not None
    assert p1.name == "Legacy Project Alpha"
    assert p1.target_seed == "alpha.example.com"

    # Assert projects exist in SQLite database directly
    db_projects = mgr.db.list_projects()
    assert len(db_projects) == 2

    # Assert projects.json was renamed to projects.json.migrated
    assert not legacy_json.exists()
    assert (tmp_path / "projects.json.migrated").exists()


def test_already_migrated_install_does_not_remigrate(tmp_path: Path):
    """When DB is already populated, it loads from DB and does not touch backup."""
    # First run to populate DB
    mgr1 = ProjectManager(data_dir=str(tmp_path))
    p = mgr1.create_project(name="Native SQLite Project", target_seed="target.org", target_type=EntityType.DOMAIN)
    assert len(mgr1.list_projects()) == 1

    # Simulate an untouched legacy file
    extra_json = tmp_path / "projects.json"
    extra_json.write_text(json.dumps([{"id": "dummy", "name": "Dummy", "target_seed": "x", "target_type": "domain"}]), encoding="utf-8")

    # Second run should read directly from SQLite without re-migrating
    mgr2 = ProjectManager(data_dir=str(tmp_path))
    assert len(mgr2.list_projects()) == 1
    assert mgr2.list_projects()[0].id == p.id
    # projects.json was not touched because DB is already populated
    assert extra_json.exists()

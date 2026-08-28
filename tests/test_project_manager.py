"""Tests for aether.core.project_manager — Project Management and Persistence."""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from aether.core.state import EntityType, InvestigationStatus
from aether.core.project_manager import ProjectManager


@pytest.fixture
def manager(tmp_path: Path):
    """Creates a temporary project manager instance for test isolation."""
    return ProjectManager(data_dir=str(tmp_path / "data"))


class TestProjectManager:
    def test_create_and_get_project(self, manager: ProjectManager):
        proj = manager.create_project(
            name="Op Phoenix",
            target_seed="@phx_target",
            target_type=EntityType.SOCIAL_HANDLE,
            context_briefing="Suspected APT operator account.",
        )
        assert proj.id is not None
        assert proj.name == "Op Phoenix"
        assert proj.target_seed == "@phx_target"
        assert proj.target_type == EntityType.SOCIAL_HANDLE
        assert proj.context_briefing == "Suspected APT operator account."
        assert proj.status == InvestigationStatus.IDLE

        # Get by ID
        fetched = manager.get_project(proj.id)
        assert fetched is not None
        assert fetched.id == proj.id
        assert fetched.name == "Op Phoenix"

    def test_auto_detect_target_type(self, manager: ProjectManager):
        p1 = manager.create_project(name="T1", target_seed="@handle")
        assert p1.target_type == EntityType.SOCIAL_HANDLE

        p2 = manager.create_project(name="T2", target_seed="target.com")
        assert p2.target_type == EntityType.DOMAIN

        p3 = manager.create_project(name="T3", target_seed="1.1.1.1")
        assert p3.target_type == EntityType.IP_ADDRESS

        p4 = manager.create_project(name="T4", target_seed="victim@test.org")
        assert p4.target_type == EntityType.EMAIL

    def test_list_projects(self, manager: ProjectManager):
        manager.create_project(name="Proj A", target_seed="a.com")
        manager.create_project(name="Proj B", target_seed="b.com")

        summaries = manager.list_projects()
        assert len(summaries) == 2
        names = {s.name for s in summaries}
        assert "Proj A" in names
        assert "Proj B" in names

    def test_update_project(self, manager: ProjectManager):
        proj = manager.create_project(name="Initial", target_seed="init.com")
        updated = manager.update_project(
            proj.id,
            name="Renamed",
            context_briefing="New notes added",
        )
        assert updated is not None
        assert updated.name == "Renamed"
        assert updated.context_briefing == "New notes added"

    def test_delete_project(self, manager: ProjectManager):
        proj = manager.create_project(name="To Delete", target_seed="delete.com")
        assert manager.get_project(proj.id) is not None

        deleted = manager.delete_project(proj.id)
        assert deleted is True
        assert manager.get_project(proj.id) is None

    def test_persistence_across_instances(self, tmp_path: Path):
        data_dir = str(tmp_path / "persistent_data")
        pm1 = ProjectManager(data_dir=data_dir)
        p = pm1.create_project(
            name="Persistent Project",
            target_seed="persist.org",
            context_briefing="Critical persistence test",
        )

        # Reload with new manager instance on same data directory
        pm2 = ProjectManager(data_dir=data_dir)
        loaded = pm2.get_project(p.id)
        assert loaded is not None
        assert loaded.name == "Persistent Project"
        assert loaded.context_briefing == "Critical persistence test"

    @pytest.mark.asyncio
    async def test_batch_queue(self, manager: ProjectManager):
        with patch.object(manager, "run_project", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = True
            p1 = manager.create_project(name="Batch 1", target_seed="b1.com")
            p2 = manager.create_project(name="Batch 2", target_seed="b2.com")

            count = await manager.run_batch_sequential([p1.id, p2.id])
            assert count == 2
            assert manager.get_project(p1.id).status in (InvestigationStatus.QUEUED, InvestigationStatus.PLANNING)
            assert manager.get_project(p2.id).status in (InvestigationStatus.QUEUED, InvestigationStatus.PLANNING)

"""Global test fixtures and environment isolation for AETHER test suite."""

import os
import pytest
from pathlib import Path

@pytest.fixture(autouse=True)
def isolate_test_data_dir(tmp_path: Path, monkeypatch):
    """Automatically redirects all AETHER project data and databases to a temp directory during tests."""
    temp_data = tmp_path / "aether_test_data"
    temp_data.mkdir(parents=True, exist_ok=True)

    # Monkeypatch settings and database locations
    try:
        from aether.config.settings import settings
        monkeypatch.setattr(settings, "DATA_DIR", temp_data)
    except Exception:
        pass

    try:
        from aether.core.project_manager import ProjectManager
        import aether.core.project_manager as pm_module
        import aether.api.server as server_module

        temp_pm = ProjectManager(data_dir=str(temp_data))
        monkeypatch.setattr(pm_module, "project_manager", temp_pm)
        monkeypatch.setattr(server_module, "project_manager", temp_pm)
    except Exception:
        pass

    return temp_data

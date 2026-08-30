"""
Migration Script — Migrates legacy data/projects.json records into SQLite database.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aether.core.db import db
from aether.core.state import Project
from aether.core.logger import logger


def migrate_projects_json():
    json_path = PROJECT_ROOT / "data" / "projects.json"
    if not json_path.exists():
        logger.info(f"No legacy projects.json found at {json_path}. Nothing to migrate.")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        migrated_count = 0
        for item in data:
            try:
                proj = Project.model_validate(item)
                db.save_project(proj)
                migrated_count += 1
            except Exception as e:
                logger.warning(f"Skipping project {item.get('id', 'unknown')}: {e}")

        logger.success(f"Successfully migrated {migrated_count} projects to SQLite database ({db.db_path})")
    except Exception as exc:
        logger.error(f"Migration failed: {exc}")


if __name__ == "__main__":
    migrate_projects_json()

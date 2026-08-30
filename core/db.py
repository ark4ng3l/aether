"""
Database Layer — SQLite-backed structured storage for AETHER projects, entities, relationships, tasks, and tool health.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from aether.config.settings import settings
from aether.core.logger import logger
from aether.core.state import (
    Project,
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
    TaskStep,
    ConfidenceSignal,
    InvestigationStatus,
    AgentState,
)


class Database:
    """Manages SQLite storage for AETHER investigations, entities, relationships, and telemetry."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "projects.db"
        )
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        """Initializes database tables and performance indices."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    target_seed TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    context_briefing TEXT DEFAULT '',
                    status TEXT NOT NULL,
                    dossier TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
                CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects(updated_at DESC);

                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT NOT NULL,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    type TEXT NOT NULL,
                    properties_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    confidence_signals_json TEXT NOT NULL DEFAULT '[]',
                    corroboration_count INTEGER NOT NULL DEFAULT 1,
                    first_seen TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (project_id, id)
                );
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(project_id, type);

                CREATE TABLE IF NOT EXISTS relationships (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    rel_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    metadata_json TEXT DEFAULT '{}',
                    PRIMARY KEY (project_id, source_id, target_id, rel_type)
                );
                CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(project_id, source_id);
                CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(project_id, target_id);

                CREATE TABLE IF NOT EXISTS task_steps (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    tool_name TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    reasoning TEXT DEFAULT '',
                    status TEXT NOT NULL,
                    verdict TEXT,
                    confidence REAL DEFAULT 0.5,
                    output_summary TEXT DEFAULT '',
                    duration_seconds REAL DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    produced_entity_ids_json TEXT DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_project_time ON task_steps(project_id, timestamp);

                CREATE TABLE IF NOT EXISTS tool_health (
                    tool_name TEXT PRIMARY KEY,
                    total_calls INTEGER DEFAULT 0,
                    total_failures INTEGER DEFAULT 0,
                    total_duration_ms REAL DEFAULT 0,
                    last_status TEXT,
                    last_called_at TEXT
                );
            """)

    # ── Project Operations ──────────────────────────────────────────────────

    def save_project(self, project: Project):
        """Inserts or updates a project record."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO projects 
                (id, name, target_seed, target_type, context_briefing, status, dossier, created_at, updated_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.name,
                    project.target_seed,
                    project.target_type.value,
                    project.context_briefing or "",
                    project.status.value,
                    project.dossier or "",
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                    project.finished_at.isoformat() if project.finished_at else None,
                ),
            )

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieves a project by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return self._row_to_project(dict(row))

    def list_projects(self) -> List[Project]:
        """Lists all projects ordered by updated_at descending."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
            return [self._row_to_project(dict(r)) for r in rows]

    def delete_project(self, project_id: str) -> bool:
        """Deletes a project and cascades to its entities, relationships, and tasks."""
        with self._connect() as conn:
            res = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return res.rowcount > 0

    # ── Entity & Provenance Operations ──────────────────────────────────────

    def save_entity(self, project_id: str, entity: Entity):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entities
                (id, project_id, type, properties_json, confidence, confidence_signals_json, corroboration_count, first_seen, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    project_id,
                    entity.type.value,
                    json.dumps(entity.properties),
                    entity.confidence,
                    json.dumps([s.model_dump() for s in entity.confidence_signals]),
                    entity.corroboration_count,
                    entity.first_seen.isoformat(),
                    entity.last_updated.isoformat(),
                ),
            )

    def get_entity_provenance(self, project_id: str, entity_id: str) -> List[Dict[str, Any]]:
        """Finds all task_steps that produced or touched this entity_id."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM task_steps WHERE project_id = ? ORDER BY timestamp ASC",
                (project_id,),
            ).fetchall()

            matching_tasks = []
            for r in rows:
                d = dict(r)
                try:
                    produced = json.loads(d.get("produced_entity_ids_json", "[]"))
                except Exception:
                    produced = []
                if entity_id in produced:
                    d["params"] = json.loads(d.get("params_json", "{}"))
                    d["produced_entity_ids"] = produced
                    matching_tasks.append(d)
            return matching_tasks

    def save_task_step(self, project_id: str, task: TaskStep):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO task_steps
                (id, project_id, tool_name, params_json, reasoning, status, verdict, confidence, output_summary, duration_seconds, timestamp, produced_entity_ids_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    project_id,
                    task.tool_name,
                    json.dumps(task.params),
                    task.reasoning or "",
                    task.status,
                    task.verdict,
                    task.confidence,
                    task.output_summary or "",
                    task.duration_seconds,
                    task.timestamp.isoformat(),
                    json.dumps(task.produced_entity_ids),
                ),
            )

    def get_project_entities(self, project_id: str) -> List[Entity]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM entities WHERE project_id = ?", (project_id,)).fetchall()
            entities = []
            for r in rows:
                try:
                    signals = [ConfidenceSignal.model_validate(s) for s in json.loads(r["confidence_signals_json"])]
                except Exception:
                    signals = []
                entities.append(
                    Entity(
                        id=r["id"],
                        type=EntityType(r["type"]),
                        properties=json.loads(r["properties_json"]),
                        confidence=r["confidence"],
                        confidence_signals=signals,
                        corroboration_count=r["corroboration_count"],
                        first_seen=datetime.fromisoformat(r["first_seen"]),
                        last_updated=datetime.fromisoformat(r["last_updated"]),
                    )
                )
            return entities

    def get_project_tasks(self, project_id: str) -> List[TaskStep]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM task_steps WHERE project_id = ? ORDER BY timestamp ASC",
                (project_id,),
            ).fetchall()
            tasks = []
            for r in rows:
                try:
                    produced = json.loads(r["produced_entity_ids_json"])
                except Exception:
                    produced = []
                tasks.append(
                    TaskStep(
                        id=r["id"],
                        tool_name=r["tool_name"],
                        params=json.loads(r["params_json"]),
                        reasoning=r["reasoning"],
                        status=r["status"],
                        verdict=r["verdict"],
                        confidence=r["confidence"],
                        output_summary=r["output_summary"],
                        duration_seconds=r["duration_seconds"],
                        timestamp=datetime.fromisoformat(r["timestamp"]),
                        produced_entity_ids=produced,
                    )
                )
            return tasks

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _row_to_project(self, d: Dict[str, Any]) -> Project:
        entities = self.get_project_entities(d["id"])
        tasks = self.get_project_tasks(d["id"])
        
        state = AgentState(
            investigation_id=d["id"],
            project_id=d["id"],
            project_name=d["name"],
            target_seed=d["target_seed"],
            target_type=EntityType(d["target_type"]),
            context_briefing=d.get("context_briefing", ""),
            status=InvestigationStatus(d["status"]),
            dossier=d.get("dossier", ""),
            discovered_entities=entities,
            completed_tasks=tasks,
        )

        return Project(
            id=d["id"],
            name=d["name"],
            target_seed=d["target_seed"],
            target_type=EntityType(d["target_type"]),
            context_briefing=d.get("context_briefing", ""),
            status=InvestigationStatus(d["status"]),
            dossier=d.get("dossier", ""),
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
            finished_at=datetime.fromisoformat(d["finished_at"]) if d.get("finished_at") else None,
            state=state,
            entities_count=len(entities),
            completed_tasks_count=len(tasks),
        )


# Global database instance
db = Database()

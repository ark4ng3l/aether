"""
ProjectManager — Central management and persistence of AETHER investigation projects.

Features:
  • Persistent storage in JSON (`aether/data/projects.json`).
  • Full CRUD: create, list, get, update, delete.
  • Execution management: single run, cancel/stop, sequential batch queue.
  • Context briefing support to condition LLM reasoning per project.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from aether.core.logger import logger
from aether.core.state import (
    AgentState,
    EntityType,
    InvestigationStatus,
    Project,
    ProjectSummary,
)
from aether.core.events import event_bus


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ProjectManager:
    """Manages creation, persistence, and execution queue of investigation projects."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or "aether/data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.data_dir / "projects.json"
        self.migrated_storage_file = self.data_dir / "projects.json.migrated"

        from aether.core.db import Database
        self.db = Database(db_path=str(self.data_dir / "projects.db"))

        self._projects: Dict[str, Project] = {}
        self._active_engines: Dict[str, Any] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._batch_queue: asyncio.Queue[str] = asyncio.Queue()
        self._batch_worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        self._load_from_disk()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_from_disk(self):
        """Loads saved projects from SQLite database as primary source of truth, with one-time JSON migration."""
        # 1. One-time legacy JSON migration: if projects.json exists and SQLite is empty
        try:
            existing_db_projects = self.db.list_projects()
            if self.storage_file.exists() and len(existing_db_projects) == 0:
                logger.info(f"Legacy {self.storage_file} found with empty SQLite DB. Running one-time migration...")
                migrated_count = 0
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for item in raw_data:
                        try:
                            proj = Project.model_validate(item)
                            self.db.save_project(proj)
                            if proj.state:
                                for ent in proj.state.discovered_entities:
                                    self.db.save_entity(proj.id, ent)
                                for tsk in proj.state.completed_tasks:
                                    self.db.save_task_step(proj.id, tsk)
                            migrated_count += 1
                        except Exception as parse_err:
                            logger.warning(f"Skipping corrupted legacy project: {parse_err}")

                # Rename projects.json -> projects.json.migrated as backup
                try:
                    self.storage_file.rename(self.migrated_storage_file)
                    logger.info(f"Renamed {self.storage_file} -> {self.migrated_storage_file}")
                except Exception as ren_err:
                    logger.warning(f"Could not rename {self.storage_file}: {ren_err}")

                logger.success(f"Migrated {migrated_count} projects to SQLite database.")
        except Exception as mig_exc:
            logger.error(f"Error during legacy JSON migration to SQLite: {mig_exc}")

        # 2. Read directly from SQLite as primary source of truth
        try:
            db_projects = self.db.list_projects()
            for proj in db_projects:
                # Reset in-progress statuses on restart
                if proj.status in (
                    InvestigationStatus.PLANNING,
                    InvestigationStatus.COLLECTING,
                    InvestigationStatus.REASONING,
                    InvestigationStatus.VERIFYING,
                    InvestigationStatus.SYNTHESIZING,
                    InvestigationStatus.QUEUED,
                ):
                    proj.status = InvestigationStatus.IDLE
                self._projects[proj.id] = proj
            logger.info(f"Loaded {len(self._projects)} projects from SQLite primary database")
        except Exception as e:
            logger.error(f"Failed to load projects from SQLite primary database: {e}")

    def _save_to_disk(self):
        """Saves all projects to SQLite primary database synchronously (source of truth)."""
        try:
            for p in self._projects.values():
                self.db.save_project(p)
                if p.state:
                    for entity in p.state.discovered_entities:
                        self.db.save_entity(p.id, entity)
                    for task in p.state.completed_tasks:
                        self.db.save_task_step(p.id, task)
        except Exception as exc:
            logger.error(f"Failed to save projects to SQLite: {exc}")

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    def create_project(
        self,
        name: str,
        target_seed: str,
        target_type: EntityType = EntityType.UNKNOWN,
        context_briefing: str = "",
    ) -> Project:
        """Create and persist a new investigation project."""
        name = name.strip() or f"Investigation {target_seed}"
        target_seed = target_seed.strip()

        # If target type is UNKNOWN, infer from seed
        if target_type == EntityType.UNKNOWN:
            if target_seed.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff", ".bmp")) or "uploads" in target_seed:
                target_type = EntityType.IMAGE
            elif target_seed.startswith("@"):
                target_type = EntityType.SOCIAL_HANDLE
            elif "@" in target_seed and "." in target_seed:
                target_type = EntityType.EMAIL
            elif target_seed.replace(".", "").replace(":", "").isdigit():
                target_type = EntityType.IP_ADDRESS
            elif "." in target_seed and " " not in target_seed:
                target_type = EntityType.DOMAIN
            else:
                target_type = EntityType.PERSON

        project = Project(
            name=name,
            target_seed=target_seed,
            target_type=target_type,
            context_briefing=context_briefing.strip(),
            status=InvestigationStatus.IDLE,
        )

        self._projects[project.id] = project
        self._save_to_disk()
        logger.info(f"Created project '{project.name}' [{project.id}]")
        return project

    def list_projects(self) -> List[ProjectSummary]:
        """Return list of all projects summarized for UI dashboard."""
        summaries = []
        for p in sorted(self._projects.values(), key=lambda x: x.updated_at, reverse=True):
            if p.id in self._active_engines:
                eng = self._active_engines[p.id]
                status = eng.state.status
                ent_count = len(eng.state.discovered_entities)
                comp_count = len(eng.state.completed_tasks)
            else:
                status = p.status
                ent_count = len(p.state.discovered_entities) if p.state else p.entities_count
                comp_count = len(p.state.completed_tasks) if p.state else p.completed_tasks_count

            summaries.append(
                ProjectSummary(
                    id=p.id,
                    name=p.name,
                    target_seed=p.target_seed,
                    target_type=p.target_type,
                    context_briefing=p.context_briefing,
                    status=status,
                    entities_count=ent_count,
                    completed_tasks_count=comp_count,
                    has_dossier=bool(p.dossier or (p.state and p.state.dossier)),
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )
        return summaries

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve full project details by ID with live state sync."""
        project = self._projects.get(project_id)
        if project and project_id in self._active_engines:
            eng = self._active_engines[project_id]
            project.status = eng.state.status
            project.state = eng.state
            project.entities_count = len(eng.state.discovered_entities)
            project.completed_tasks_count = len(eng.state.completed_tasks)
        return project

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        context_briefing: Optional[str] = None,
        target_seed: Optional[str] = None,
        target_type: Optional[EntityType] = None,
    ) -> Optional[Project]:
        """Update editable metadata of a project."""
        project = self._projects.get(project_id)
        if not project:
            return None

        if name is not None:
            project.name = name.strip()
        if context_briefing is not None:
            project.context_briefing = context_briefing.strip()
        if target_seed is not None:
            project.target_seed = target_seed.strip()
        if target_type is not None:
            project.target_type = target_type

        project.updated_at = _now_utc()
        self._save_to_disk()
        return project

    def delete_project(self, project_id: str) -> bool:
        """Stop any running execution, purge collected graph/vectors, and delete the project."""
        if project_id in self._active_tasks and not self._active_tasks[project_id].done():
            self._active_tasks[project_id].cancel()

        # 1. Purge and delete isolated SQLite Graph database for this project
        try:
            graph_db = Path(f"aether/data/graphs/{project_id}.db")
            if graph_db.exists():
                graph_db.unlink()
                logger.info(f"Purged graph database for project [{project_id}]")
        except Exception as exc:
            logger.warning(f"Could not remove graph db for {project_id}: {exc}")

        # 2. Purge vector store points for this project
        try:
            from aether.memory.vector_store import VectorStore
            vs = VectorStore()
            vs.delete_by_project(project_id)
        except Exception:
            pass

        # 3. Clean up SQLite database record
        try:
            self.db.delete_project(project_id)
        except Exception as exc:
            logger.warning(f"Could not delete SQLite record for {project_id}: {exc}")

        # 4. Clean up in-memory engines and records
        if project_id in self._projects:
            del self._projects[project_id]
            self._active_engines.pop(project_id, None)
            self._active_tasks.pop(project_id, None)
            self._save_to_disk()
            logger.info(f"Deleted project [{project_id}] and purged all associated data.")
            return True
        return False

    # ------------------------------------------------------------------
    # Execution & Batch Queue
    # ------------------------------------------------------------------

    async def run_project(self, project_id: str) -> bool:
        """Start execution of a single project."""
        project = self._projects.get(project_id)
        if not project:
            return False

        # If already running, return True
        if project_id in self._active_tasks and not self._active_tasks[project_id].done():
            return True

        from aether.orchestration.engine import OrchestrationEngine

        engine = OrchestrationEngine(
            target_seed=project.target_seed,
            project_id=project.id,
            project_name=project.name,
            target_type=project.target_type,
            context_briefing=project.context_briefing,
        )

        self._active_engines[project_id] = engine
        project.status = InvestigationStatus.PLANNING
        project.state = engine.state
        project.updated_at = _now_utc()
        self._save_to_disk()

        async def _run_wrapper():
            try:
                await engine.run_investigation()
            except asyncio.CancelledError:
                logger.warning(f"Project [{project_id}] execution cancelled.")
                engine.state.status = InvestigationStatus.STOPPED
            except Exception as exc:
                logger.error(f"Project [{project_id}] failed: {exc}")
                engine.state.status = InvestigationStatus.FAILED
                engine.state.last_error = str(exc)
            finally:
                # Sync state back to project
                project.status = engine.state.status
                project.state = engine.state
                project.dossier = engine.dossier
                project.entities_count = len(engine.state.discovered_entities)
                project.completed_tasks_count = len(engine.state.completed_tasks)
                project.finished_at = _now_utc()
                project.updated_at = _now_utc()
                self._save_to_disk()
                await event_bus.emit(
                    project.id,
                    {
                        "type": "project_finished",
                        "data": {
                            "project_id": project.id,
                            "status": project.status.value,
                            "entities_count": project.entities_count,
                            "completed_tasks": project.completed_tasks_count,
                        },
                    },
                )
                await event_bus.emit_global({
                    "type": "project_updated",
                    "data": {"project_id": project.id, "status": project.status.value},
                })

        task = asyncio.create_task(_run_wrapper())
        self._active_tasks[project_id] = task
        return True

    def stop_project(self, project_id: str) -> bool:
        """Stop an active project run."""
        task = self._active_tasks.get(project_id)
        if task and not task.done():
            task.cancel()

        engine = self._active_engines.get(project_id)
        if engine:
            engine.state.status = InvestigationStatus.STOPPED

        project = self._projects.get(project_id)
        if project:
            project.status = InvestigationStatus.STOPPED
            project.updated_at = _now_utc()
            self._save_to_disk()
            asyncio.create_task(event_bus.emit(project_id, {"type": "status_change", "data": {"status": "stopped"}}))
            asyncio.create_task(event_bus.emit_global({"type": "project_updated", "data": {"project_id": project_id, "status": "stopped"}}))
            return True
        return False

    async def run_batch_sequential(self, project_ids: Optional[List[str]] = None) -> int:
        """
        Queue multiple projects to run sequentially one after another.
        Prevents VRAM collisions and concurrency overload.
        """
        targets = project_ids or list(self._projects.keys())
        queued_count = 0

        for pid in targets:
            proj = self._projects.get(pid)
            if proj and proj.status not in (
                InvestigationStatus.PLANNING,
                InvestigationStatus.COLLECTING,
                InvestigationStatus.REASONING,
                InvestigationStatus.VERIFYING,
                InvestigationStatus.SYNTHESIZING,
            ):
                proj.status = InvestigationStatus.QUEUED
                proj.updated_at = _now_utc()
                await self._batch_queue.put(pid)
                queued_count += 1

        self._save_to_disk()

        # Start batch worker if not already running
        if self._batch_worker_task is None or self._batch_worker_task.done():
            self._batch_worker_task = asyncio.create_task(self._batch_worker())

        return queued_count

    async def _batch_worker(self):
        """Worker that processes queued projects one by one sequentially."""
        logger.info("Batch sequential worker started.")
        while not self._batch_queue.empty():
            project_id = await self._batch_queue.get()
            proj = self._projects.get(project_id)
            if not proj:
                continue

            logger.mission_critical(f"Batch worker starting project: '{proj.name}' [{project_id}]")
            await self.run_project(project_id)

            # Wait for active task to complete
            task = self._active_tasks.get(project_id)
            if task:
                try:
                    await task
                except Exception:
                    pass
            # Short cooldown between models to release VRAM
            await asyncio.sleep(1.0)

        logger.info("Batch sequential queue finished.")

    # ------------------------------------------------------------------
    # Graph & Dossier Access
    # ------------------------------------------------------------------

    def get_project_graph(self, project_id: str) -> Dict[str, Any]:
        """Fetch Cytoscape graph nodes and edges for this project."""
        engine = self._active_engines.get(project_id)
        if engine:
            nodes = engine.graph_store.query_all_nodes()
            edges = engine.graph_store.query_all_edges()
        else:
            project_db = Path(f"aether/data/graphs/{project_id}.db")
            if project_db.exists():
                from aether.memory.graph_store import GraphStore
                store = GraphStore(db_path=str(project_db))
                nodes = store.query_all_nodes()
                edges = store.query_all_edges()
            else:
                project = self._projects.get(project_id)
                if not project or not project.state:
                    return {"nodes": [], "edges": []}
                # Reconstruct from saved state
                nodes = [
                    {
                        "id": e.id,
                        "type": e.type.value,
                        "properties": e.properties,
                        "confidence": e.confidence,
                    }
                    for e in project.state.discovered_entities
                ]
                edges = []

        cy_nodes = []
        for n in nodes:
            props = n.get("properties", {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except Exception:
                    props = {}
            if not isinstance(props, dict):
                props = {}

            label = props.get("name") or props.get("label")
            if not label:
                ntype = n.get("type", "unknown")
                nid = str(n["id"])
                if "_" in nid:
                    prefix = nid.split("_")[0]
                    label = prefix.replace("_", " ").title()
                else:
                    label = nid

            cy_nodes.append({
                "data": {
                    "id": n["id"],
                    "type": n.get("type", "unknown"),
                    "label": label,
                    "properties": props,
                    "confidence": n.get("confidence", 1.0),
                }
            })
        cy_edges = [
            {
                "data": {
                    "source": e["source_id"],
                    "target": e["target_id"],
                    "label": e["rel_type"],
                    "weight": e.get("weight", 1.0),
                }
            }
            for e in edges
        ]
        return {"nodes": cy_nodes, "edges": cy_edges}


# Global singleton
project_manager = ProjectManager()

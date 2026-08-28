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
        """Loads saved projects from disk at startup."""
        if not self.storage_file.exists():
            return
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for item in raw_data:
                    try:
                        proj = Project.model_validate(item)
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
                    except Exception as e:
                        logger.warning(f"Skipping corrupted project record: {e}")
            logger.info(f"Loaded {len(self._projects)} projects from {self.storage_file}")
        except Exception as exc:
            logger.error(f"Failed to load projects from {self.storage_file}: {exc}")

    def _save_to_disk(self):
        """Saves all projects to disk synchronously."""
        try:
            data = [p.model_dump(mode="json") for p in self._projects.values()]
            tmp_file = self.storage_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp_file.replace(self.storage_file)
        except Exception as exc:
            logger.error(f"Failed to save projects to disk: {exc}")

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
            if target_seed.startswith("@"):
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
            ent_count = len(p.state.discovered_entities) if p.state else p.entities_count
            comp_count = len(p.state.completed_tasks) if p.state else p.completed_tasks_count
            summaries.append(
                ProjectSummary(
                    id=p.id,
                    name=p.name,
                    target_seed=p.target_seed,
                    target_type=p.target_type,
                    context_briefing=p.context_briefing,
                    status=p.status,
                    entities_count=ent_count,
                    completed_tasks_count=comp_count,
                    has_dossier=bool(p.dossier or (p.state and p.state.dossier)),
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )
        return summaries

    def get_project(self, project_id: str) -> Optional[Project]:
        """Retrieve full project details by ID."""
        return self._projects.get(project_id)

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
        """Stop any running execution and delete the project."""
        if project_id in self._active_tasks and not self._active_tasks[project_id].done():
            self._active_tasks[project_id].cancel()

        if project_id in self._projects:
            del self._projects[project_id]
            self._active_engines.pop(project_id, None)
            self._active_tasks.pop(project_id, None)
            self._save_to_disk()
            logger.info(f"Deleted project [{project_id}]")
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
            project = self._projects.get(project_id)
            if project:
                project.status = InvestigationStatus.STOPPED
                project.updated_at = _now_utc()
                self._save_to_disk()
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

        cy_nodes = [
            {
                "data": {
                    "id": n["id"],
                    "type": n.get("type", "unknown"),
                    "label": n.get("properties", {}).get("name", n["id"])
                    if isinstance(n.get("properties"), dict)
                    else n["id"],
                    "properties": n.get("properties", {}),
                    "confidence": n.get("confidence", 1.0),
                }
            }
            for n in nodes
        ]
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

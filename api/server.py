from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure project and parent directory in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
PARENT_DIR = BASE_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aether.core.logger import logger
from aether.core.state import EntityType, InvestigationStatus
from aether.core.project_manager import project_manager
from aether.core.events import event_bus

app = FastAPI(title="AETHER Intelligence Engine API", version="2.0.0")

# Enable CORS for full UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UI_FILE = BASE_DIR / "ui" / "index.html"


# ── Request Models ────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: Optional[str] = ""
    target_seed: str
    target_type: Optional[EntityType] = EntityType.UNKNOWN
    context_briefing: Optional[str] = ""


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    target_seed: Optional[str] = None
    target_type: Optional[EntityType] = None
    context_briefing: Optional[str] = None


class InjectTaskRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any]
    reasoning: Optional[str] = "Manual operator injection"


# ── Root & Static UI ──────────────────────────────────────────────────────────

@app.get("/")
async def root():
    if UI_FILE.exists():
        return FileResponse(UI_FILE)
    return {"status": "online", "engine": "AETHER"}


@app.get("/api/health")
async def health():
    return {"status": "online", "engine": "AETHER", "version": "2.0.0"}


# ── Project Management Endpoints ──────────────────────────────────────────────

@app.get("/api/projects")
async def list_projects():
    """List all projects summarized for dashboard."""
    summaries = project_manager.list_projects()
    return {"projects": [s.model_dump(mode="json") for s in summaries]}


@app.post("/api/projects")
async def create_project(req: CreateProjectRequest):
    """Create a new investigation project."""
    if not req.target_seed.strip():
        raise HTTPException(status_code=400, detail="target_seed cannot be empty")

    project = project_manager.create_project(
        name=req.name or f"Investigation {req.target_seed}",
        target_seed=req.target_seed,
        target_type=req.target_type or EntityType.UNKNOWN,
        context_briefing=req.context_briefing or "",
    )
    return {"status": "created", "project": project.model_dump(mode="json")}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Retrieve full project details."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": proj.model_dump(mode="json")}


@app.patch("/api/projects/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest):
    """Update editable project fields."""
    proj = project_manager.update_project(
        project_id=project_id,
        name=req.name,
        target_seed=req.target_seed,
        target_type=req.target_type,
        context_briefing=req.context_briefing,
    )
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "updated", "project": proj.model_dump(mode="json")}


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and cancel its active run."""
    success = project_manager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted", "project_id": project_id}


# ── Execution Controls ────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/run")
async def run_project(project_id: str):
    """Start investigation execution for a single project."""
    success = await project_manager.run_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found or failed to start")
    return {"status": "started", "project_id": project_id}


@app.post("/api/projects/{project_id}/stop")
async def stop_project(project_id: str):
    """Stop an active project run."""
    stopped = project_manager.stop_project(project_id)
    return {"status": "stopped" if stopped else "not_running", "project_id": project_id}


@app.post("/api/projects/run-all")
async def run_all_projects():
    """Queue all idle/pending projects to execute sequentially."""
    count = await project_manager.run_batch_sequential()
    return {"status": "queued", "count": count}


@app.post("/api/projects/{project_id}/inject-task")
async def inject_task(project_id: str, req: InjectTaskRequest):
    """Inject a dynamic task into an active or queued project."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # If engine instance exists
    engine = project_manager._active_runs.get(project_id)
    if engine:
        engine.inject_task(req.tool_name, req.params, req.reasoning or "Manual injection")
    else:
        if proj.state:
            proj.state.current_task_stack.append(f"{req.tool_name}: {req.params}")
            project_manager.save_projects()

    return {"status": "injected", "tool": req.tool_name, "params": req.params}


# ── Project Intelligence Artifacts ────────────────────────────────────────────

@app.get("/api/projects/{project_id}/graph")
async def get_project_graph(project_id: str):
    """Get nodes and edges formatted for Cytoscape.js."""
    graph_data = project_manager.get_project_graph(project_id)
    return graph_data


@app.get("/api/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str):
    """Get active, pending, and completed task history for pipeline stepper."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    state = proj.state
    active_task = state.active_task.model_dump(mode="json") if (state and state.active_task) else None
    completed_tasks = [t.model_dump(mode="json") for t in state.completed_tasks] if state else []
    active_hypotheses = state.active_hypotheses if state else []
    pending_tasks = state.current_task_stack if state else []

    return {
        "project_id": project_id,
        "status": proj.status.value,
        "active_task": active_task,
        "active_hypotheses": active_hypotheses,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks,
    }


@app.get("/api/projects/{project_id}/dossier")
async def get_project_dossier(project_id: str):
    """Get generated intelligence dossier."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    dossier = proj.dossier or (proj.state.dossier if proj.state else "")
    return {"project_id": project_id, "dossier": dossier}


@app.get("/api/projects/{project_id}/export/stix")
async def export_project_stix(project_id: str):
    """Exports project findings as an official STIX 2.1 Threat Intel Bundle."""
    import uuid
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    graph = project_manager.get_project_graph(project_id)
    stix_objects = []

    # 1. Identity
    identity_id = f"identity--{uuid.uuid4()}"
    stix_objects.append({
        "type": "identity",
        "spec_version": "2.1",
        "id": identity_id,
        "created": proj.created_at.isoformat() if proj.created_at else "2026-08-28T00:00:00Z",
        "modified": proj.updated_at.isoformat() if proj.updated_at else "2026-08-28T00:00:00Z",
        "name": proj.target_seed,
        "identity_class": "unknown",
        "description": proj.context_briefing or f"Target of AETHER investigation: {proj.name}",
    })

    # 2. Convert graph nodes to STIX SDOs
    node_stix_map = {}
    for node in graph.get("nodes", []):
        ndata = node.get("data", {})
        nid = ndata.get("id", "")
        ntype = ndata.get("type", "artifact")
        stix_id = f"infrastructure--{uuid.uuid4()}" if ntype in ("ip_address", "domain") else f"indicator--{uuid.uuid4()}"
        node_stix_map[nid] = stix_id

        stix_objects.append({
            "type": "infrastructure" if ntype in ("ip_address", "domain") else "indicator",
            "spec_version": "2.1",
            "id": stix_id,
            "created": proj.created_at.isoformat() if proj.created_at else "2026-08-28T00:00:00Z",
            "modified": proj.updated_at.isoformat() if proj.updated_at else "2026-08-28T00:00:00Z",
            "name": ndata.get("label", nid),
            "description": f"AETHER discovered {ntype}: {nid}",
            "confidence": int(ndata.get("confidence", 0.8) * 100),
            "custom_properties": ndata.get("properties", {}),
        })

    # 3. Convert edges to STIX Relationships
    for edge in graph.get("edges", []):
        edata = edge.get("data", {})
        src = edata.get("source")
        tgt = edata.get("target")
        if src in node_stix_map and tgt in node_stix_map:
            stix_objects.append({
                "type": "relationship",
                "spec_version": "2.1",
                "id": f"relationship--{uuid.uuid4()}",
                "created": proj.created_at.isoformat() if proj.created_at else "2026-08-28T00:00:00Z",
                "modified": proj.updated_at.isoformat() if proj.updated_at else "2026-08-28T00:00:00Z",
                "relationship_type": edata.get("label", "related-to").lower().replace("_", "-"),
                "source_ref": node_stix_map[src],
                "target_ref": node_stix_map[tgt],
            })

    bundle = {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid4()}",
        "spec_version": "2.1",
        "objects": stix_objects,
    }
    return bundle


@app.get("/api/projects/{project_id}/timeline")
async def get_project_timeline(project_id: str):
    """Returns chronological timeline events of all discovery milestones."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    events = []
    events.append({
        "timestamp": proj.created_at.isoformat() if proj.created_at else "",
        "title": "Investigation Initialized",
        "category": "milestone",
        "description": f"Target Seed: {proj.target_seed} ({proj.target_type.value})",
    })

    if proj.state and proj.state.completed_tasks:
        for t in proj.state.completed_tasks:
            events.append({
                "timestamp": proj.updated_at.isoformat() if proj.updated_at else "",
                "title": f"Executed: {t.tool_name}",
                "category": "recon",
                "description": f"Verdict: {t.verdict} ({int(t.confidence * 100)}% conf) — {t.reasoning}",
                "summary": t.output_summary[:180],
            })

    graph = project_manager.get_project_graph(project_id)
    for n in graph.get("nodes", []):
        ndata = n.get("data", {})
        events.append({
            "timestamp": proj.updated_at.isoformat() if proj.updated_at else "",
            "title": f"Entity Discovered: [{ndata.get('type', 'entity').upper()}]",
            "category": "entity",
            "description": ndata.get("label", ndata.get("id")),
            "properties": ndata.get("properties", {}),
        })

    return {"project_id": project_id, "events": events}


# ── Image Upload & Image OSINT Endpoints ─────────────────────────────────────

@app.post("/api/upload/image")
async def upload_image_endpoint(file: UploadFile = File(...)):
    """Uploads an image file to local storage for Image OSINT investigation."""
    import uuid
    upload_dir = BASE_DIR / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "image.jpg").suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"):
        ext = ".jpg"

    unique_filename = f"upload_{uuid.uuid4().hex[:8]}{ext}"
    saved_path = upload_dir / unique_filename

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    return {
        "status": "uploaded",
        "file_path": str(saved_path),
        "filename": unique_filename,
        "original_filename": file.filename,
        "size_bytes": len(content),
    }


@app.get("/api/images/{filename}")
async def get_uploaded_image(filename: str):
    """Serves uploaded images for UI previews."""
    image_path = BASE_DIR / "data" / "uploads" / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


# ── Capabilities & Tool Hub Endpoints ────────────────────────────────────────

class ExecuteToolRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class SynthesizeToolRequest(BaseModel):
    description: str


@app.get("/api/tools")
async def list_tools_endpoint():
    """List all registered OSINT and perception tools with capability metadata."""
    from aether.perception.tools.registry import registry
    return {"tools": registry.list_tools(), "count": len(registry.list_tools())}


@app.post("/api/tools/execute")
async def execute_tool_endpoint(req: ExecuteToolRequest):
    """Executes a specific tool live on-demand for monitoring and verification."""
    import time
    from aether.perception.tools.registry import registry
    tool = registry.get_tool(req.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found")

    t_start = time.time()
    try:
        res = await tool.execute(**req.params)
        duration_ms = round((time.time() - t_start) * 1000, 2)
        res.execution_time_ms = duration_ms
        return {
            "tool_name": req.tool_name,
            "execution_time_ms": duration_ms,
            "success": res.success,
            "data": res.data,
            "error": res.error,
        }
    except Exception as exc:
        duration_ms = round((time.time() - t_start) * 1000, 2)
        return {
            "tool_name": req.tool_name,
            "execution_time_ms": duration_ms,
            "success": False,
            "data": {},
            "error": str(exc),
        }


@app.post("/api/tools/synthesize")
async def synthesize_tool_endpoint(req: SynthesizeToolRequest):
    """Synthesizes a new custom OSINT tool using Hermes 35B and registers it live."""
    from aether.core.tool_maker import synthesize_custom_tool
    result = await synthesize_custom_tool(req.description)
    return result




# ── Legacy & Quick Investigate Compatibility ─────────────────────────────────

@app.post("/api/investigate/{seed:path}")
@app.post("/investigate/{seed:path}")
async def investigate_legacy(seed: str):
    """Legacy quick scan endpoint: creates or uses existing project and starts run."""
    existing = next((p for p in project_manager._projects.values() if p.target_seed == seed), None)
    if not existing:
        existing = project_manager.create_project(
            name=f"Quick Scan: {seed}",
            target_seed=seed,
        )
    await project_manager.run_project(existing.id)
    return {"status": "started", "seed": seed, "project_id": existing.id}


@app.get("/api/status/{seed:path}")
@app.get("/status/{seed:path}")
async def get_status_legacy(seed: str):
    proj = next((p for p in project_manager._projects.values() if p.target_seed == seed or p.id == seed), None)
    if proj:
        return {"status": proj.status.value, "project_id": proj.id}
    return {"status": "not_found"}


# ── Neural Settings & Model Matrix Endpoints ─────────────────────────────────

class UpdateSettingsRequest(BaseModel):
    OLLAMA_BASE_URL: Optional[str] = None
    MODEL_AGGRESSIVE_FAST: Optional[str] = None
    MODEL_VLM: Optional[str] = None
    MODEL_FAST: Optional[str] = None
    MODEL_CRITIC: Optional[str] = None
    MODEL_DEEP: Optional[str] = None
    MODEL_DEEP_FALLBACK: Optional[str] = None
    MODEL_DEEP_31B: Optional[str] = None
    HYPOTHESIS_RECURSION_LIMIT: Optional[int] = None
    MAX_SEARCH_DEPTH: Optional[int] = None
    ENTITY_CONFIDENCE_THRESHOLD: Optional[float] = None
    REASONING_TEMPERATURE: Optional[float] = None
    PLANNER_TEMPERATURE: Optional[float] = None
    CRITIC_TEMPERATURE: Optional[float] = None
    MAX_CONCURRENT_HEAVY_MODELS: Optional[int] = None
    VRAM_ARBITRATION_ENABLED: Optional[bool] = None


@app.get("/api/settings")
async def get_settings():
    """Fetch current system configuration and available Ollama models."""
    from aether.config.settings import settings
    import httpx

    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
    except Exception as exc:
        logger.warning(f"Could not fetch Ollama models: {exc}")

    return {
        "settings": {
            "OLLAMA_BASE_URL": settings.OLLAMA_BASE_URL,
            "MODEL_AGGRESSIVE_FAST": settings.MODEL_AGGRESSIVE_FAST,
            "MODEL_VLM": settings.MODEL_VLM,
            "MODEL_FAST": settings.MODEL_FAST,
            "MODEL_CRITIC": settings.MODEL_CRITIC,
            "MODEL_DEEP": settings.MODEL_DEEP,
            "MODEL_DEEP_FALLBACK": settings.MODEL_DEEP_FALLBACK,
            "MODEL_DEEP_31B": settings.MODEL_DEEP_31B,
            "HYPOTHESIS_RECURSION_LIMIT": settings.HYPOTHESIS_RECURSION_LIMIT,
            "MAX_SEARCH_DEPTH": settings.MAX_SEARCH_DEPTH,
            "ENTITY_CONFIDENCE_THRESHOLD": settings.ENTITY_CONFIDENCE_THRESHOLD,
            "REASONING_TEMPERATURE": settings.REASONING_TEMPERATURE,
            "PLANNER_TEMPERATURE": settings.PLANNER_TEMPERATURE,
            "CRITIC_TEMPERATURE": settings.CRITIC_TEMPERATURE,
            "MAX_CONCURRENT_HEAVY_MODELS": settings.MAX_CONCURRENT_HEAVY_MODELS,
            "VRAM_ARBITRATION_ENABLED": settings.VRAM_ARBITRATION_ENABLED,
        },
        "available_models": ollama_models,
    }


@app.post("/api/settings")
async def update_settings_endpoint(req: UpdateSettingsRequest):
    """Update and persist AETHER model and reasoning settings."""
    from aether.config.settings import settings
    updates = req.model_dump(exclude_none=True)
    settings.update_and_save(updates)
    logger.info("Updated AETHER neural & reasoning configuration.")
    return {"status": "updated", "settings": updates}


@app.get("/api/system/update-check")
async def check_for_updates():
    """Checks GitHub for new commits, tags, and releases."""
    from aether.core.updater import check_github_update
    update_info = await check_github_update()
    return update_info



# ── WebSocket Real-Time Streaming ─────────────────────────────────────────────

@app.websocket("/ws/{channel_id:path}")
async def websocket_stream(websocket: WebSocket, channel_id: str):
    """
    WebSocket endpoint for real-time telemetry, stepper updates, and graph changes.
    Supports subscribing by project_id, investigation_id, or 'global'/'main'.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for channel: '{channel_id}'")

    sub_key = channel_id
    matching_proj = next((p for p in project_manager._projects.values() if p.target_seed == channel_id), None)
    if matching_proj:
        sub_key = matching_proj.id

    queue = event_bus.subscribe(sub_key)

    try:
        await websocket.send_json({
            "type": "heartbeat",
            "data": {"channel": channel_id, "status": "connected"},
        })

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "data": {"channel": channel_id, "ping": "ok"},
                })
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from channel: '{channel_id}'")
    except Exception as exc:
        logger.warning(f"WebSocket error on channel '{channel_id}': {exc}")
    finally:
        event_bus.unsubscribe(sub_key, queue)
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

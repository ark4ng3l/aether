from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure project and parent directory in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
PARENT_DIR = BASE_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import secrets
import re
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, File, UploadFile, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aether.core.logger import logger
from aether.core.state import EntityType, InvestigationStatus
from aether.core.project_manager import project_manager
from aether.core.events import event_bus

# ── Local API Security Token ──────────────────────────────────────────────────
AUTH_TOKEN_FILE = BASE_DIR / "data" / ".session_token"
AUTH_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
if not AUTH_TOKEN_FILE.exists():
    legacy_file = BASE_DIR / "data" / "auth_token.txt"
    if legacy_file.exists():
        AUTH_TOKEN = legacy_file.read_text(encoding="utf-8").strip()
    else:
        AUTH_TOKEN = secrets.token_hex(24)
    AUTH_TOKEN_FILE.write_text(AUTH_TOKEN, encoding="utf-8")
    try:
        os.chmod(AUTH_TOKEN_FILE, 0o600)
    except Exception:
        pass
    logger.mission_critical(f"AETHER Local API Security Token: {AUTH_TOKEN}")
    logger.mission_critical(f"AETHER Dashboard Login URL: http://127.0.0.1:8000/#token={AUTH_TOKEN}")
else:
    AUTH_TOKEN = AUTH_TOKEN_FILE.read_text(encoding="utf-8").strip()
    try:
        os.chmod(AUTH_TOKEN_FILE, 0o600)
    except Exception:
        pass

app = FastAPI(title="AETHER Intelligence Engine API", version="3.0.0")

# Enable secure CORS for Localhost / 127.0.0.1
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple In-Memory Rate Limiting ────────────────────────────────────────────
class SlidingWindowRateLimiter:
    def __init__(self, default_limit: int = 120, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str, limit: Optional[int] = None) -> bool:
        now = time.time()
        max_reqs = limit or self.default_limit
        cutoff = now - self.window_seconds

        async with self._lock:
            history = self._requests.get(client_ip, [])
            valid_history = [t for t in history if t > cutoff]
            if len(valid_history) >= max_reqs:
                self._requests[client_ip] = valid_history
                return False
            valid_history.append(now)
            self._requests[client_ip] = valid_history
            return True

rate_limiter = SlidingWindowRateLimiter(default_limit=240, window_seconds=60)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Localhost gets higher threshold (600 req/min) vs remote clients (120 req/min)
    limit = 600 if client_ip in ("127.0.0.1", "localhost", "::1") else 120
    allowed = await rate_limiter.is_allowed(client_ip, limit=limit)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests. Rate limit exceeded. Please slow down."},
            headers={"Retry-After": "15"},
        )
    return await call_next(request)
@app.middleware("http")
async def local_auth_middleware(request: Request, call_next):
    path = request.url.path
    # Allow public endpoints
    if (
        path == "/"
        or path == "/api/health"
        or path == "/api/auth/token"
        or path == "/api/auth/session"
        or path.startswith("/docs")
        or path.startswith("/redoc")
        or path.startswith("/openapi.json")
        or not path.startswith("/api/")
    ):
        return await call_next(request)

    # Check Bearer token in header, ?token= param, or cookie
    auth_header = request.headers.get("Authorization", "")
    query_token = request.query_params.get("token", "")
    cookie_token = request.cookies.get("aether_token", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif query_token:
        token = query_token.strip()
    elif cookie_token:
        token = cookie_token.strip()

    if token != AUTH_TOKEN:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized. Bearer token required for API access."},
        )

    return await call_next(request)

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
UI_FILE = FRONTEND_DIST / "index.html" if FRONTEND_DIST.exists() else BASE_DIR / "ui" / "index.html"

if FRONTEND_DIST.exists() and (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


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

@app.get("/aether_logo.png")
@app.get("/logo.png")
@app.get("/favicon.png")
async def get_static_logo():
    """Serves the primary AETHER cyber-intelligence logo."""
    candidates = [
        FRONTEND_DIST / "aether_logo.png",
        FRONTEND_DIST / "logo.png",
        BASE_DIR / "frontend" / "public" / "aether_logo.png",
        BASE_DIR / "assets" / "aether_logo.png",
        BASE_DIR / "docs" / "assets" / "aether_logo.png",
    ]
    for c in candidates:
        if c.exists():
            return FileResponse(c, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo asset not found")


@app.get("/favicon.ico")
async def get_favicon():
    """Serves favicon icon."""
    candidates = [
        FRONTEND_DIST / "favicon.ico",
        FRONTEND_DIST / "aether_logo.png",
        BASE_DIR / "frontend" / "public" / "aether_logo.png",
        BASE_DIR / "assets" / "aether_logo.png",
    ]
    for c in candidates:
        if c.exists():
            return FileResponse(c, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/")
async def root(request: Request):
    if UI_FILE.exists():
        html = UI_FILE.read_text(encoding="utf-8")
        bootstrap_script = f'<script>window.__AETHER_BOOT_TOKEN__ = "{AUTH_TOKEN}"; window.__AETHER_BOOTSTRAP__ = {{ token: "{AUTH_TOKEN}" }};</script>'
        if "</head>" in html:
            html = html.replace("</head>", f"{bootstrap_script}</head>")
        else:
            html = f"{bootstrap_script}{html}"

        resp = Response(content=html, media_type="text/html")
        resp.set_cookie(key="aether_token", value=AUTH_TOKEN, httponly=False, samesite="lax", max_age=86400 * 30)
        return resp
    return {"status": "online", "engine": "AETHER"}


@app.get("/api/auth/session")
@app.get("/api/auth/token")
async def get_session_token():
    """Returns local session token for authenticated localhost client initialization."""
    return {"token": AUTH_TOKEN, "status": "authenticated"}


@app.get("/api/health")
async def health():
    """Deep system health diagnostics covering Database, Memory Stores, and Telemetry."""
    db_ok = False
    active_projects_count = 0
    try:
        active_projects_count = len(project_manager._projects)
        # Test SQLite connection
        db_projects = project_manager.db.list_projects()
        db_ok = True
    except Exception as exc:
        logger.error(f"Health check DB probe error: {exc}")

    from aether.perception.tools.registry import registry
    from aether.core.cache import response_cache, circuit_breaker
    from aether.core.resource_arbiter import resource_arbiter
    from aether.core.tor_manager import tor_manager

    return {
        "status": "online",
        "engine": "AETHER",
        "version": "3.0.0",
        "diagnostics": {
            "database_connected": db_ok,
            "registered_tools_count": len(registry.list_tools()),
            "active_projects_count": active_projects_count,
            "cache_entries_count": len(response_cache._store),
            "circuit_breakers_tripped": any(s.get("degraded", False) for s in circuit_breaker.get_status().values()),
            "resource_arbiter": resource_arbiter.get_telemetry(),
            "tor_status": tor_manager.get_status(),
        }
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown handler: cancels active background engines and cleanly terminates daemons."""
    logger.info("AETHER Server is shutting down... Initiating graceful cleanup.")
    # 1. Stop all active project runs
    for pid in list(project_manager._active_tasks.keys()):
        project_manager.stop_project(pid)

    # 2. Stop watchdog if active
    try:
        from aether.core.watchdog import watchdog_daemon
        watchdog_daemon.stop()
    except Exception:
        pass

    # 3. Stop embedded Tor daemon if active
    try:
        from aether.core.tor_manager import tor_manager
        if tor_manager.is_running:
            await tor_manager.stop()
    except Exception:
        pass

    logger.info("AETHER graceful shutdown complete.")


# ── Embedded Tor Daemon Controller Endpoints ──────────────────────────────────

@app.get("/api/tor/status")
async def get_tor_status():
    """Returns the current status, bootstrap progress, and SOCKS5 proxy info of the embedded Tor daemon."""
    from aether.core.tor_manager import tor_manager
    return tor_manager.get_status()


@app.post("/api/tor/start")
async def start_tor_daemon():
    """Starts the embedded Tor core daemon (automatically downloads binaries if not already present)."""
    from aether.core.tor_manager import tor_manager
    ok = await tor_manager.start()
    return {
        "success": ok,
        "status": tor_manager.get_status(),
        "error": tor_manager.last_error if not ok else None,
    }


@app.post("/api/tor/stop")
async def stop_tor_daemon():
    """Stops the embedded Tor core daemon."""
    from aether.core.tor_manager import tor_manager
    ok = await tor_manager.stop()
    return {"success": ok, "status": tor_manager.get_status()}


@app.post("/api/tor/bootstrap")
async def bootstrap_tor():
    """Downloads and extracts the standalone Tor core binary into data/tor/."""
    from aether.core.tor_manager import tor_manager
    ok = await tor_manager.bootstrap_binaries()
    return {
        "success": ok,
        "installed": tor_manager.is_installed,
        "status": tor_manager.get_status(),
        "error": tor_manager.last_error if not ok else None,
    }


@app.post("/api/tor/new-circuit")
async def rotate_tor_circuit():
    """Sends SIGNAL NEWNYM to rotate the Tor identity and obtain a fresh circuit/exit IP."""
    from aether.core.tor_manager import tor_manager
    if not tor_manager.is_running:
        raise HTTPException(status_code=400, detail="Tor daemon is not running")
    ok = await tor_manager.new_circuit()
    ip_info = await tor_manager.get_exit_ip(force_refresh=True)
    return {"success": ok, "exit_ip_info": ip_info}


@app.get("/api/tor/exit-ip")
async def get_tor_exit_ip(refresh: bool = False):
    """Verifies and returns the active Tor exit IP via the local SOCKS5 proxy."""
    from aether.core.tor_manager import tor_manager
    return await tor_manager.get_exit_ip(force_refresh=refresh)


@app.get("/api/tor/version")
async def get_tor_version():
    """Returns local Tor binary engine version and installed bundle version."""
    from aether.core.tor_manager import tor_manager
    return tor_manager.get_installed_version()


@app.get("/api/tor/check-update")
async def check_tor_update():
    """Scans official Tor Project archive to check if a newer release bundle is available."""
    from aether.core.tor_manager import tor_manager
    return await tor_manager.check_updates()


@app.post("/api/tor/update")
async def update_tor_bundle(payload: Optional[Dict[str, Any]] = None):
    """Performs in-place hot upgrade to latest (or specified) Tor Expert Bundle version."""
    from aether.core.tor_manager import tor_manager
    target_v = payload.get("version") if payload else None
    return await tor_manager.upgrade(target_version=target_v)


# ── Stealth, Anti-Fingerprinting & Proxy Chain Endpoints ──────────────────────

@app.get("/api/stealth/status")
async def get_stealth_status():
    """Returns active synthetic browser persona, anti-fingerprinting status, and proxy gateway routing."""
    from aether.core.stealth_engine import stealth_engine
    return stealth_engine.get_status()


@app.post("/api/stealth/rotate-persona")
async def rotate_stealth_persona():
    """Generates a fresh synthetic browser fingerprint persona (OS, resolution, canvas seed, user-agent)."""
    from aether.core.stealth_engine import stealth_engine
    persona = stealth_engine.generate_persona()
    return {"status": "rotated", "persona": persona.to_dict()}


@app.post("/api/stealth/proxies")
async def configure_stealth_proxies(payload: Dict[str, Any]):
    """Configures proxy strategy and registers custom HTTP/SOCKS5 proxy lists."""
    from aether.core.stealth_engine import stealth_engine
    strategy = payload.get("strategy")
    proxies = payload.get("proxies")

    if strategy:
        try:
            stealth_engine.set_proxy_strategy(strategy)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    if proxies is not None and isinstance(proxies, list):
        stealth_engine.add_proxies(proxies)

    return stealth_engine.get_status()


@app.get("/api/stealth/check-leak")
async def check_stealth_leak():
    """Tests the stealth client against leak detection endpoints to verify proxy routing and header anonymity."""
    from aether.core.stealth_engine import stealth_engine
    try:
        async with stealth_engine.create_stealth_client(timeout=15.0) as client:
            resp = await client.get("https://httpbin.org/headers")
            headers_echo = resp.json().get("headers", {}) if resp.status_code == 200 else {}

        return {
            "leak_test_passed": True,
            "persona_headers_applied": "Sec-Ch-Ua" in headers_echo or "User-Agent" in headers_echo,
            "echoed_headers": headers_echo,
            "active_proxy": stealth_engine.get_active_proxy(),
        }
    except Exception as exc:
        return {
            "leak_test_passed": False,
            "error": str(exc),
            "active_proxy": stealth_engine.get_active_proxy(),
        }


# ── Advanced Forensic Intelligence Endpoints ─────────────────────────────────

@app.post("/api/intelligence/resolve-entities")
async def resolve_entities_endpoint(payload: Dict[str, Any]):
    """Resolves whether two cross-platform profiles belong to the same person with multi-dimensional scoring."""
    from aether.reasoning.entity_resolver import entity_resolver
    prof_a = payload.get("profile_a", {})
    prof_b = payload.get("profile_b", {})
    if not prof_a or not prof_b:
        raise HTTPException(status_code=400, detail="Requires profile_a and profile_b objects")
    result = entity_resolver.resolve_profiles(prof_a, prof_b)
    return result.to_dict()


@app.post("/api/intelligence/stylometry")
async def stylometry_endpoint(payload: Dict[str, Any]):
    """Compares linguistic habits and authorship probability between two text samples."""
    from aether.reasoning.entity_resolver import stylometry_analyzer
    sample_a = payload.get("sample_a", "")
    sample_b = payload.get("sample_b", "")
    if not sample_a or not sample_b:
        raise HTTPException(status_code=400, detail="Requires sample_a and sample_b text strings")
    return stylometry_analyzer.compare_authorship(sample_a, sample_b)


@app.post("/api/intelligence/temporal-rhythm")
async def temporal_rhythm_endpoint(payload: Dict[str, Any]):
    """Analyzes timestamped activity to deduce circadian sleep cycles and geographical UTC timezone."""
    from aether.reasoning.entity_resolver import temporal_estimator
    timestamps = payload.get("timestamps", [])
    if not timestamps:
        raise HTTPException(status_code=400, detail="Requires timestamps array")
    return temporal_estimator.estimate_timezone(timestamps)


@app.post("/api/intelligence/social-matrix")
async def social_matrix_endpoint(payload: Dict[str, Any]):
    """Scans 50+ platforms with tri-detection and regex filters for target username."""
    from aether.perception.tools.social_matrix_tools import social_matrix_scanner
    user = payload.get("username", "")
    cats = payload.get("categories")
    use_tor = payload.get("use_tor", False)
    if not user:
        raise HTTPException(status_code=400, detail="Requires username field")
    return await social_matrix_scanner(username=user, categories=cats, use_tor=use_tor)


@app.post("/api/intelligence/permutations")
async def permutations_endpoint(payload: Dict[str, Any]):
    """Generates combinatorial and leetspeak username mutations from identity components."""
    from aether.reasoning.handle_permutator import handle_permutator
    return {
        "success": True,
        "permutations": handle_permutator.generate(
            first_name=payload.get("first_name", ""),
            last_name=payload.get("last_name", ""),
            handle=payload.get("handle", ""),
            birth_year=payload.get("birth_year"),
            company=payload.get("company", ""),
            limit=payload.get("limit", 50),
        ),
    }


@app.post("/api/intelligence/avatar-match")
async def avatar_match_endpoint(payload: Dict[str, Any]):
    """Compares perceptual image hashes (dHash/aHash) across profiles."""
    from aether.reasoning.avatar_comparator import avatar_comparator
    hash_a = payload.get("hash_a", "")
    hash_b = payload.get("hash_b", "")
    if not hash_a or not hash_b:
        raise HTTPException(status_code=400, detail="Requires hash_a and hash_b")
    return avatar_comparator.compare_hashes(hash_a, hash_b)


@app.post("/api/intelligence/web-check")
async def web_check_endpoint(payload: Dict[str, Any]):
    """Runs all-in-one Web-Check diagnostic suite (DNS, SSL, Standards, Redirects, WAF, Carbon)."""
    from aether.perception.tools.web_check_suite import web_check_full_audit
    domain = payload.get("domain", "")
    if not domain:
        raise HTTPException(status_code=400, detail="Requires domain field")
    return await web_check_full_audit(domain)


@app.post("/api/intelligence/chronolocate")
async def chronolocate_endpoint(payload: Dict[str, Any]):
    """Calculates solar elevation/azimuth or estimates photo capture time from shadow length."""
    from aether.perception.tools.geospatial_intelligence import sun_chronolocator
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Requires latitude and longitude")
    return sun_chronolocator(
        latitude=float(lat),
        longitude=float(lon),
        utc_timestamp=payload.get("utc_timestamp"),
        shadow_length_meters=payload.get("shadow_length_meters"),
        object_height_meters=payload.get("object_height_meters"),
        target_date=payload.get("target_date"),
    )


@app.get("/api/intelligence/frameworks/mitre")
async def get_cyber_frameworks_summary():
    """Returns MITRE ATT&CK v19.1, D3FEND, and Fight Fraud F3 framework matrix summary."""
    from aether.reasoning.cyber_frameworks import cyber_frameworks
    return cyber_frameworks.get_matrix_summary()


@app.post("/api/auth/token/regenerate")
async def regenerate_auth_token():
    """Generates and persists a new Bearer auth token, invalidating the previous one."""
    global AUTH_TOKEN
    AUTH_TOKEN = secrets.token_hex(24)
    AUTH_TOKEN_FILE.write_text(AUTH_TOKEN, encoding="utf-8")
    try:
        os.chmod(AUTH_TOKEN_FILE, 0o600)
    except Exception:
        pass
    logger.mission_critical(f"AETHER Auth Token Regenerated.")
    return {"status": "regenerated", "token": AUTH_TOKEN}


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
    engine = project_manager._active_engines.get(project_id)
    if engine:
        engine.inject_task(req.tool_name, req.params, req.reasoning or "Manual injection")
    else:
        if proj.state:
            proj.state.current_task_stack.append(f"{req.tool_name}: {req.params}")
            project_manager._save_to_disk()

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


@app.get("/api/projects/{project_id}/entities/{entity_id}/provenance")
async def get_entity_provenance_endpoint(project_id: str, entity_id: str):
    """Returns task_steps that produced or touched this entity for provenance tracking."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    from aether.core.db import db
    tasks = db.get_entity_provenance(project_id, entity_id)

    # Fallback to in-memory state if SQLite doesn't have it yet
    if not tasks and proj.state:
        for t in proj.state.completed_tasks:
            if entity_id in t.produced_entity_ids or entity_id in t.output_summary:
                tasks.append(t.model_dump(mode="json"))

    return {"project_id": project_id, "entity_id": entity_id, "provenance_tasks": tasks}


@app.get("/api/projects/{project_id}/dossier")
async def get_project_dossier(project_id: str):
    """Get generated intelligence dossier."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    dossier = proj.dossier or (proj.state.dossier if proj.state else "")
    return {"project_id": project_id, "dossier": dossier}


@app.get("/api/projects/{project_id}/dossier/export")
async def export_dossier_consolidated(
    project_id: str,
    format: str = Query("json", description="Export format: pdf, stix, json, or md"),
):
    """Consolidated dossier export endpoint supporting pdf, stix, json, and md formats."""
    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    dossier_text = proj.dossier or (proj.state.dossier if proj.state else "")

    if format == "stix":
        return await export_project_stix(project_id)
    elif format == "md":
        return Response(
            content=dossier_text,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=dossier_{project_id}.md"},
        )
    elif format == "pdf":
        html_content = (
            f"<html><head><title>AETHER Dossier - {proj.name}</title>"
            f"<style>body{{font-family:sans-serif;padding:40px;background:#fff;color:#111;line-height:1.6;}}"
            f"h1,h2{{color:#003366;}}</style></head><body>"
            f"<h1>AETHER Intelligence Dossier: {proj.name}</h1>"
            f"<p><b>Target Seed:</b> {proj.target_seed} ({proj.target_type.value})</p><hr/>"
            f"<pre style='white-space:pre-wrap;'>{dossier_text}</pre></body></html>"
        )
        return Response(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": f"inline; filename=dossier_{project_id}.html"},
        )
    else:
        return {
            "project_id": project_id,
            "name": proj.name,
            "target_seed": proj.target_seed,
            "target_type": proj.target_type.value,
            "dossier": dossier_text,
            "created_at": proj.created_at.isoformat(),
            "finished_at": proj.finished_at.isoformat() if proj.finished_at else None,
        }


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


# ── Next-Gen Threat Modeling & Direct Tool Execution ───────────────────────────

@app.post("/api/projects/{project_id}/threat-model")
async def generate_threat_model(project_id: str, inject_nodes: bool = Query(False)):
    """Runs automated MITRE ATT&CK correlation on all discovered entities."""
    from aether.reasoning.attack_mapper import attack_mapper

    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    entities = proj.state.discovered_entities if proj.state else []
    techniques = attack_mapper.analyze_entities(entities)

    injected_count = 0
    if inject_nodes and proj.state and techniques:
        attack_nodes = attack_mapper.generate_attack_path_nodes(techniques, proj.target_seed)
        for node in attack_nodes:
            proj.state.add_entity(node)
            try:
                project_manager.db.save_entity(project_id, node)
            except Exception:
                pass
            injected_count += 1
        project_manager._save_to_disk()

    return {
        "project_id": project_id,
        "target_seed": proj.target_seed,
        "total_techniques_matched": len(techniques),
        "injected_nodes_count": injected_count,
        "mitre_techniques": techniques,
    }


@app.post("/api/projects/{project_id}/execute-tool-direct")
async def execute_tool_direct(project_id: str, req: InjectTaskRequest):
    """Executes any registered perception tool immediately and merges results into project graph."""
    from aether.perception.tools.registry import registry
    from aether.core.state import TaskStep
    from aether.core.events import event_bus

    proj = project_manager.get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    tool = registry.get_tool(req.tool_name)
    if not tool:
        raise HTTPException(status_code=400, detail=f"Tool '{req.tool_name}' not found in registry")

    step = TaskStep(
        id=f"direct_{req.tool_name}_{uuid.uuid4().hex[:6]}",
        tool_name=req.tool_name,
        params=req.params,
        reasoning=req.reasoning or "Direct operator pivot",
        status="running",
    )
    if proj.state:
        proj.state.current_task_stack.append(step.tool_name)

    result = await tool.execute(**req.params)

    step.status = "completed" if result.success else "failed"
    step.output_summary = f"Direct execution of {req.tool_name}: {'Success' if result.success else 'Failed'}"

    if proj.state:
        proj.state.completed_tasks.append(step)
        project_manager._save_to_disk()

    event_bus.publish(project_id, {
        "type": "tool_executed",
        "data": {
            "tool": req.tool_name,
            "params": req.params,
            "success": result.success,
            "result": result.data if result.success else result.error,
        }
    })

    return {
        "status": "completed",
        "tool": req.tool_name,
        "success": result.success,
        "data": result.data,
        "error": result.error,
    }


@app.post("/api/watchdog/check")
async def trigger_watchdog_check():
    """Triggers an immediate watchdog delta inspection across all projects."""
    from aether.core.watchdog import watchdog_daemon
    deltas = await watchdog_daemon.run_all_checks()
    return {
        "status": "completed",
        "projects_checked": len(project_manager._projects),
        "deltas_found": len(deltas),
        "deltas": [d.to_dict() for d in deltas],
    }


@app.get("/api/watchdog/status")
async def get_watchdog_status():
    """Returns the real-time operational status of the Watchdog Daemon."""
    from aether.core.watchdog import watchdog_daemon
    from aether.config.settings import settings
    return {
        "enabled": settings.WATCHDOG_ENABLED,
        "running": watchdog_daemon._running,
        "interval_hours": settings.WATCHDOG_INTERVAL_HOURS,
        "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        "discord_configured": bool(settings.DISCORD_WEBHOOK_URL),
    }


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
    """Serves uploaded images for UI previews with strict path validation."""
    if not re.match(r"^[a-zA-Z0-9_\-]+\.(jpg|jpeg|png|webp|gif|bmp|tiff)$", filename, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Invalid filename format")

    upload_dir = (BASE_DIR / "data" / "uploads").resolve()
    image_path = (upload_dir / filename).resolve()

    if not str(image_path).startswith(str(upload_dir)) or not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


class AnalyzeImageRequest(BaseModel):
    filename: Optional[str] = None
    image_path: Optional[str] = None
    prompt: Optional[str] = "Analyze this image for OSINT intelligence: identify any readable text, location clues, landmarks, equipment, or logos."


@app.post("/api/images/analyze")
async def analyze_image_endpoint(req: AnalyzeImageRequest):
    """Runs deep multimodal forensics, EXIF extraction, OCR, and scene analysis on an uploaded image."""
    from aether.perception.tools.image_tools import ImageOSINTTool
    filename = req.filename or req.image_path or ""
    if not filename:
        raise HTTPException(status_code=400, detail="Filename or image_path required")

    upload_dir = (BASE_DIR / "data" / "uploads").resolve()
    # Security: only allow basename to prevent path traversal
    safe_name = Path(filename).name
    target_path = (upload_dir / safe_name).resolve()
    # Verify resolved path is still within upload_dir
    if not str(target_path).startswith(str(upload_dir)):
        raise HTTPException(status_code=400, detail="Invalid file path — access denied")
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Image file '{safe_name}' not found in uploads")

    tool = ImageOSINTTool()
    result = await tool.execute(image_path=str(target_path), prompt=req.prompt)
    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error,
        "execution_time_ms": result.execution_time_ms,
    }



# [REMOVED] Duplicate /api/auth/token/regenerate endpoint — consolidated at line ~191



# ── System Metrics & Observability ────────────────────────────────────────────

@app.get("/api/metrics")
async def get_metrics_endpoint():
    """Returns system health, tool success rates, uptime, and resource arbiter telemetry."""
    from aether.core.metrics import metrics_collector
    from aether.core.resource_arbiter import resource_arbiter
    from aether.core.cache import circuit_breaker

    summary = metrics_collector.get_summary()
    summary["resource_arbiter"] = resource_arbiter.get_telemetry()
    summary["circuit_breakers"] = circuit_breaker.get_status()
    return summary


# ── Capabilities & Tool Hub Endpoints ────────────────────────────────────────

class ExecuteToolRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class SynthesizeToolRequest(BaseModel):
    description: str
    auto_register: Optional[bool] = False


@app.get("/api/tools")
async def list_tools_endpoint():
    """List all registered OSINT and perception tools with capability metadata."""
    from aether.perception.tools.registry import registry
    return {"tools": registry.list_tools(), "count": len(registry.list_tools())}


@app.get("/api/tools/staged")
async def get_staged_tools_endpoint():
    """Lists all synthesized tools awaiting human approval."""
    from aether.core.tool_maker import list_staged_tools
    return {"staged_tools": list_staged_tools()}


@app.post("/api/tools/approve/{stage_id}")
@app.post("/api/tools/synthesize/{stage_id}/approve")
async def approve_tool_endpoint(stage_id: str):
    """Approves and registers a staged tool."""
    from aether.core.tool_maker import approve_and_register_tool
    result = approve_and_register_tool(stage_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/tools/reject/{stage_id}")
@app.post("/api/tools/synthesize/{stage_id}/reject")
async def reject_tool_endpoint(stage_id: str):
    """Rejects a staged tool draft."""
    from aether.core.tool_maker import _staged_tools
    if stage_id in _staged_tools:
        _staged_tools[stage_id]["status"] = "rejected"
        return {"status": "rejected", "stage_id": stage_id}
    raise HTTPException(status_code=404, detail="Staged tool draft not found")


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
    """Synthesizes a new custom OSINT tool with AST validation and stages it for approval."""
    from aether.core.tool_maker import synthesize_custom_tool
    result = await synthesize_custom_tool(req.description, auto_register=bool(req.auto_register))
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
    LLM_PROVIDER: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = None
    CUSTOM_API_BASE_URL: Optional[str] = None
    CUSTOM_API_KEY: Optional[str] = None
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
            "LLM_PROVIDER": settings.LLM_PROVIDER,
            "OLLAMA_BASE_URL": settings.OLLAMA_BASE_URL,
            "CUSTOM_API_BASE_URL": settings.CUSTOM_API_BASE_URL,
            "CUSTOM_API_KEY": settings.CUSTOM_API_KEY,
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
@app.get("/api/system/update/check")
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
    
    NOTE: Browser WebSocket API does not allow custom headers during the initial handshake,
    so validating token via ?token= query parameter is a deliberate, scoped exception.
    """
    ws_token = websocket.query_params.get("token", "").strip()
    if ws_token != AUTH_TOKEN:
        await websocket.close(code=1008, reason="Unauthorized")
        return

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

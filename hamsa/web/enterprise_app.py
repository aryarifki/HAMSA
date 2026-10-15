"""
HAMSA Enterprise ASGI Application
High-performance async web service built on FastAPI and Uvicorn.
Provides native Server-Sent Events (SSE) streaming, PostgreSQL connection pooling,
interactive OpenAPI/Swagger documentation, and multi-case investigation management.
"""

import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from hamsa.core.database import GLOBAL_DB
from hamsa.core.orchestrator import Orchestrator
from hamsa.core.models import TargetType
from hamsa.core.cache import GLOBAL_CACHE
from hamsa.core.sources import SourceManager
from hamsa.core.reporting import ReportGenerator
from hamsa.utils.formatters import log_info, log_success

# Global Enterprise Orchestrator
GLOBAL_ORCHESTRATOR = Orchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and graceful shutdown lifecycles."""
    log_info("Starting HAMSA Enterprise Intelligence Service...")
    await GLOBAL_DB.connect()
    yield
    log_info("Shutting down HAMSA Enterprise Intelligence Service...")
    await GLOBAL_DB.close()


app = FastAPI(
    title="HAMSA Enterprise Intelligence Platform",
    description="Autonomous OSINT Reconnaissance, Knowledge Graph Correlation, and Case Dossier Management API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Pydantic Request & Response Schemas
# ------------------------------------------------------------------------------

class ScanRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    depth: int = Field(default=2, ge=1, le=5)
    case_id: str = Field(default="case_default")
    all_sites: bool = False


class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=2)
    description: str = ""
    case_id: Optional[str] = None
    tags: List[str] = ["Active"]


class AnnotateNodeRequest(BaseModel):
    node_id: str
    tag: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


class CaseNotesRequest(BaseModel):
    notes: str


class EvidenceCaptureRequest(BaseModel):
    case_id: str = "case_default"
    url: str
    title: str = "Web Capture"
    notes: str = ""


class WatchlistRequest(BaseModel):
    action: str = Field(default="add", pattern="^(add|remove)$")
    target: str
    target_type: str = "username"
    webhook: Optional[str] = None


# ------------------------------------------------------------------------------
# Health & Status
# ------------------------------------------------------------------------------

@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check and database engine status."""
    return {
        "status": "online",
        "platform": "HAMSA Enterprise OSINT Suite",
        "version": "2.0.0",
        "database_engine": GLOBAL_DB.engine_type,
        "database_connected": GLOBAL_DB._connected,
        "cache_engine": os.getenv("HAMSA_CACHE_ENGINE", "memory")
    }


# ------------------------------------------------------------------------------
# Multi-Case Dossier Management
# ------------------------------------------------------------------------------

@app.get("/api/cases", tags=["Cases"])
async def list_cases():
    """Returns all investigation cases and dossiers."""
    cases = await GLOBAL_DB.list_cases()
    return {"cases": cases}


@app.post("/api/cases", tags=["Cases"])
async def create_case(payload: CaseCreateRequest):
    """Creates a new isolated investigation case."""
    case = await GLOBAL_DB.create_case(
        title=payload.title,
        description=payload.description,
        case_id=payload.case_id,
        tags=payload.tags
    )
    return {"success": True, "case": case}


@app.get("/api/cases/{case_id}", tags=["Cases"])
async def get_case_detail(case_id: str):
    """Fetches full case details, graph data, and evidence."""
    case = await GLOBAL_DB.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.post("/api/cases/{case_id}/annotate", tags=["Cases"])
async def annotate_case_node(case_id: str, payload: AnnotateNodeRequest):
    """Applies investigator markings (Primary Suspect, Verified Lead, custom color)."""
    ok = await GLOBAL_DB.annotate_node(
        case_id=case_id,
        node_id=payload.node_id,
        tag=payload.tag,
        color=payload.color,
        notes=payload.notes
    )
    return {"success": ok}


@app.post("/api/cases/{case_id}/notes", tags=["Cases"])
async def save_case_notes(case_id: str, payload: CaseNotesRequest):
    """Updates investigator case notes."""
    ok = await GLOBAL_DB.update_case_notes(case_id, payload.notes)
    return {"success": ok}


@app.post("/api/evidence/capture", tags=["Cases"])
async def capture_evidence(payload: EvidenceCaptureRequest):
    """Saves digital forensic snapshot evidence into the case dossier."""
    ev = await GLOBAL_DB.add_evidence(
        case_id=payload.case_id,
        url=payload.url,
        title=payload.title,
        notes=payload.notes
    )
    return {"success": True, "evidence": ev}


# ------------------------------------------------------------------------------
# Knowledge Graph & Timeline
# ------------------------------------------------------------------------------

@app.get("/api/graph", tags=["Knowledge Graph"])
async def get_graph(case_id: Optional[str] = None):
    """Retrieves the knowledge graph for a case or the global active session."""
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
        if graph.nodes:
            return graph.to_dict()
    return GLOBAL_ORCHESTRATOR.graph.to_dict()


@app.get("/api/timeline", tags=["Knowledge Graph"])
async def get_timeline(case_id: str = "case_default"):
    """Extracts chronological events (EXIF dates, breach years, malware logs)."""
    events = await GLOBAL_DB.get_timeline_events(case_id)
    return {"case_id": case_id, "events": events}


# ------------------------------------------------------------------------------
# Real-Time Event Streaming (Server-Sent Events)
# ------------------------------------------------------------------------------

@app.get("/api/scan/stream", tags=["Scanning"])
async def stream_scan(
    username: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    depth: int = Query(default=2, ge=1, le=5),
    case_id: str = Query(default="case_default"),
    all_sites: bool = False
):
    """
    Streams live OSINT reconnaissance events (Server-Sent Events).
    Emits node_added, edge_added, and agent_insight as entities are detected.
    """
    targets = []
    if username:
        targets.append((username, TargetType.USERNAME))
    if email:
        targets.append((email, TargetType.EMAIL))
    if phone:
        targets.append((phone, TargetType.PHONE))

    async def event_generator():
        yield f"event: connected\ndata: {json.dumps({'status': 'streaming_ready', 'case_id': case_id, 'targets': [t[0] for t in targets]})}\n\n"

        if not targets:
            yield f"event: error\ndata: {json.dumps({'message': 'No valid targets supplied'})}\n\n"
            return

        queue = asyncio.Queue()

        def on_event_cb(evt_name: str, evt_data: Any):
            asyncio.create_task(queue.put((evt_name, evt_data)))

        # Run scan in background task
        async def run_scan_coro():
            try:
                graph = await GLOBAL_ORCHESTRATOR.scan(
                    targets=targets,
                    context={"all_sites": all_sites},
                    max_depth=depth,
                    recursive=True,
                    on_event=on_event_cb
                )
                # Persist to database
                await GLOBAL_DB.save_graph(case_id, graph, targets=targets)
                await queue.put(("saved_to_case", {"case_id": case_id, "nodes": len(graph.nodes), "edges": len(graph.edges)}))
            except Exception as e:
                await queue.put(("error", {"message": str(e)}))
            finally:
                await queue.put(None)  # Sentinel to finish generator

        scan_task = asyncio.create_task(run_scan_coro())

        while True:
            item = await queue.get()
            if item is None:
                break
            evt_name, evt_data = item
            yield f"event: {evt_name}\ndata: {json.dumps(evt_data, ensure_ascii=False)}\n\n"

        await scan_task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/scan", tags=["Scanning"])
async def trigger_scan(payload: ScanRequest):
    """Executes a standard asynchronous scan and persists results to PostgreSQL."""
    targets = []
    if payload.username:
        targets.append((payload.username, TargetType.USERNAME))
    if payload.email:
        targets.append((payload.email, TargetType.EMAIL))
    if payload.phone:
        targets.append((payload.phone, TargetType.PHONE))

    if not targets:
        raise HTTPException(status_code=400, detail="At least one target (username, email, phone) is required.")

    context = {"all_sites": payload.all_sites}
    graph = await GLOBAL_ORCHESTRATOR.scan(targets, context=context, max_depth=payload.depth, recursive=True)

    # Persist to enterprise database
    await GLOBAL_DB.save_graph(payload.case_id, graph, targets=targets)

    return graph.to_dict()


# ------------------------------------------------------------------------------
# Continuous Surveillance & Watchlist
# ------------------------------------------------------------------------------

@app.get("/api/watchlist", tags=["Surveillance"])
async def get_watchlist():
    """Lists all monitored surveillance targets."""
    from hamsa.core.watchlist import GLOBAL_WATCHLIST
    return {"targets": GLOBAL_WATCHLIST.list_targets()}


@app.post("/api/watchlist", tags=["Surveillance"])
async def manage_watchlist(payload: WatchlistRequest):
    """Adds or removes a target from the continuous surveillance watchlist."""
    from hamsa.core.watchlist import GLOBAL_WATCHLIST
    if payload.action == "add":
        success = GLOBAL_WATCHLIST.add(payload.target, payload.target_type, webhook_url=payload.webhook)
    else:
        success = GLOBAL_WATCHLIST.remove(payload.target, payload.target_type)
    return {"success": success, "targets": GLOBAL_WATCHLIST.list_targets()}


@app.post("/api/watchlist/check", tags=["Surveillance"])
async def check_watchlist_drift():
    """Executes perimeter diff scan across all watchlist targets."""
    from hamsa.core.watchlist import GLOBAL_WATCHLIST
    from hamsa.core.diff import ScanDiffEngine

    results = []
    engine = ScanDiffEngine()
    for item in GLOBAL_WATCHLIST.list_targets():
        val = item["target"]
        typ_str = item["type"]
        typ = TargetType(typ_str) if typ_str in [t.value for t in TargetType] else TargetType.USERNAME
        g_now = await GLOBAL_ORCHESTRATOR.scan([(val, typ)], max_depth=1)
        prev = GLOBAL_WATCHLIST.get_snapshot(val, typ_str)
        diff = engine.compute_diff(prev, g_now.to_dict()) if prev else None
        score = engine.calculate_drift_score(diff) if diff else 0
        GLOBAL_WATCHLIST.save_snapshot(val, typ_str, g_now.to_dict(), drift_score=score)
        results.append({"target": val, "type": typ_str, "drift_score": score, "diff": diff})

    return {"status": "checked", "count": len(results), "results": results}


# ------------------------------------------------------------------------------
# Cache & Sources
# ------------------------------------------------------------------------------

@app.get("/api/cache/stats", tags=["Cache"])
async def cache_stats():
    """Returns L1 Memory LRU and L2 Redis cache metrics."""
    return GLOBAL_CACHE.stats()


@app.post("/api/cache/clear", tags=["Cache"])
async def cache_clear():
    """Clears L1/L2 cache entries."""
    GLOBAL_CACHE.clear()
    return {"status": "cleared"}


@app.post("/api/reset", tags=["System"])
async def system_reset():
    """Resets in-memory graphs and flushes cache."""
    GLOBAL_CACHE.clear()
    GLOBAL_ORCHESTRATOR.graph.clear()
    return {"status": "reset", "nodes": 0, "edges": 0}


@app.post("/api/update-sources", tags=["System"])
async def update_sources():
    """Syncs community database definitions (690+ WhatsMyName platforms)."""
    sm = SourceManager()
    count = await sm.update_sources()
    return {"status": "success", "platforms_synced": count}


@app.get("/api/report", tags=["Reporting"])
async def export_report(format: str = Query("html", pattern="^(html|markdown)$"), case_id: str = "case_default"):
    """Generates an executive forensic dossier report (HTML printable or Markdown)."""
    case = await GLOBAL_DB.get_case(case_id)
    graph = await GLOBAL_DB.load_graph(case_id) if case else GLOBAL_ORCHESTRATOR.graph
    gen = ReportGenerator(graph)

    title = case.get("title", "HAMSA Forensic Intelligence Dossier") if case else "HAMSA Intelligence Dossier"
    if format == "html":
        content = gen.to_html(title=title)
        return HTMLResponse(content)
    else:
        content = gen.to_markdown(title=title)
        return JSONResponse({"format": "markdown", "content": content})

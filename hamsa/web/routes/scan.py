"""
OSINT Reconnaissance & Scanning Router.
Handles recursive reconnaissance execution, real-time Server-Sent Events (SSE) radar streaming,
and persistent background scan job tracking in PostgreSQL.
"""

import json
import asyncio
from typing import Optional, Any
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from hamsa.core.database import GLOBAL_DB
from hamsa.core.models import TargetType
from hamsa.web.deps import GLOBAL_ORCHESTRATOR
from hamsa.web.schemas import ScanRequest

router = APIRouter(prefix="/api/scan", tags=["Scanning"])


@router.get("/stream")
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
    Emits scan_started, node_added, edge_added, and agent_insight as entities are detected.
    Persists scan execution status and results into the enterprise database.
    """
    targets = []
    if username:
        targets.append((username, TargetType.USERNAME))
    if email:
        targets.append((email, TargetType.EMAIL))
    if phone:
        targets.append((phone, TargetType.PHONE))

    async def event_generator():
        if not targets:
            yield f"event: error\ndata: {json.dumps({'message': 'No valid targets supplied'})}\n\n"
            return

        # Initialize scan job record in database
        scan_id = await GLOBAL_DB.create_scan_record(case_id=case_id, targets=targets, depth=depth)

        yield f"event: connected\ndata: {json.dumps({'status': 'streaming_ready', 'scan_id': scan_id, 'case_id': case_id, 'targets': [t[0] for t in targets]})}\n\n"

        queue = asyncio.Queue()

        def on_event_cb(evt_name: str, evt_data: Any):
            asyncio.create_task(queue.put((evt_name, evt_data)))

        # Run scan as asynchronous task
        async def run_scan_coro():
            try:
                graph = await GLOBAL_ORCHESTRATOR.scan(
                    targets=targets,
                    context={"all_sites": all_sites},
                    max_depth=depth,
                    recursive=True,
                    on_event=on_event_cb
                )
                # Persist graph into enterprise database
                await GLOBAL_DB.save_graph(case_id, graph, targets=targets)
                await GLOBAL_DB.update_scan_progress(scan_id=scan_id, status="completed", progress_percent=100)
                await queue.put(("saved_to_case", {"scan_id": scan_id, "case_id": case_id, "nodes": len(graph.nodes), "edges": len(graph.edges)}))
            except Exception as e:
                await GLOBAL_DB.update_scan_progress(scan_id=scan_id, status="failed", progress_percent=0)
                await queue.put(("error", {"message": str(e)}))
            finally:
                await queue.put(None)  # Sentinel to terminate generator loop

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


@router.post("")
async def trigger_scan(payload: ScanRequest):
    """Executes a standard asynchronous scan and tracks progress in the enterprise database."""
    targets = []
    if payload.username:
        targets.append((payload.username, TargetType.USERNAME))
    if payload.email:
        targets.append((payload.email, TargetType.EMAIL))
    if payload.phone:
        targets.append((payload.phone, TargetType.PHONE))

    if not targets:
        raise HTTPException(status_code=400, detail="At least one target (username, email, phone) is required.")

    scan_id = await GLOBAL_DB.create_scan_record(case_id=payload.case_id, targets=targets, depth=payload.depth)
    try:
        context = {"all_sites": payload.all_sites}
        graph = await GLOBAL_ORCHESTRATOR.scan(targets, context=context, max_depth=payload.depth, recursive=True)

        # Persist to enterprise database
        await GLOBAL_DB.save_graph(payload.case_id, graph, targets=targets)
        await GLOBAL_DB.update_scan_progress(scan_id=scan_id, status="completed", progress_percent=100)

        result = graph.to_dict()
        result["scan_id"] = scan_id
        return result
    except Exception as e:
        await GLOBAL_DB.update_scan_progress(scan_id=scan_id, status="failed", progress_percent=0)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_scan_history(case_id: str = "case_default"):
    """Lists past scan executions and states for a specific case."""
    scans = await GLOBAL_DB.list_scans(case_id)
    return {"case_id": case_id, "scans": scans}

"""
Knowledge Graph & Forensic Timeline Router.
Provides graph topology retrieval and chronoforensic timeline extraction.
"""

from typing import Optional
from fastapi import APIRouter
from hamsa.core.database import GLOBAL_DB
from hamsa.web.deps import GLOBAL_ORCHESTRATOR

router = APIRouter(prefix="/api", tags=["Knowledge Graph"])


@router.get("/graph")
async def get_graph(case_id: Optional[str] = None):
    """Retrieves the knowledge network graph for a specific case or the global active session."""
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
        if graph.nodes:
            return graph.to_dict()
    return GLOBAL_ORCHESTRATOR.graph.to_dict()


@router.get("/timeline")
async def get_timeline(case_id: str = "case_default"):
    """Extracts chronological events (EXIF camera timestamps, breach incident dates, malware logs)."""
    events = await GLOBAL_DB.get_timeline_events(case_id)
    return {"case_id": case_id, "events": events}

"""
Case & Investigation Dossier Management Router.
Handles case listing, creation, investigator notes, node markings, and digital evidence capture.
"""

from fastapi import APIRouter, HTTPException
from hamsa.core.database import GLOBAL_DB
from hamsa.web.schemas import (
    CaseCreateRequest,
    AnnotateNodeRequest,
    CaseNotesRequest,
    EvidenceCaptureRequest,
)

router = APIRouter(tags=["Cases"])


@router.get("/api/cases")
async def list_cases():
    """Returns all active and archived investigation dossiers with entity counts."""
    cases = await GLOBAL_DB.list_cases()
    return {"cases": cases}


@router.post("/api/cases")
async def create_case(payload: CaseCreateRequest):
    """Creates a new isolated investigation case dossier."""
    case = await GLOBAL_DB.create_case(
        title=payload.title,
        description=payload.description,
        case_id=payload.case_id,
        tags=payload.tags
    )
    return {"success": True, "case": case}


@router.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    """Fetches full case details, graph data, targets, and evidence."""
    case = await GLOBAL_DB.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case dossier '{case_id}' not found.")
    return case


@router.post("/api/cases/{case_id}/annotate")
async def annotate_case_node(case_id: str, payload: AnnotateNodeRequest):
    """Applies investigator markings (Primary Suspect, Verified Lead, custom color) to an entity node."""
    ok = await GLOBAL_DB.annotate_node(
        case_id=case_id,
        node_id=payload.node_id,
        tag=payload.tag,
        color=payload.color,
        notes=payload.notes
    )
    return {"success": ok}


@router.post("/api/cases/{case_id}/notes")
async def save_case_notes(case_id: str, payload: CaseNotesRequest):
    """Updates investigator case notes and observations for the dossier."""
    ok = await GLOBAL_DB.update_case_notes(case_id, payload.notes)
    return {"success": ok}


@router.post("/api/evidence/capture")
async def capture_evidence(payload: EvidenceCaptureRequest):
    """Saves a digital forensic snapshot evidence into the case dossier."""
    ev = await GLOBAL_DB.add_evidence(
        case_id=payload.case_id,
        url=payload.url,
        title=payload.title,
        notes=payload.notes
    )
    return {"success": True, "evidence": ev}

"""
Continuous Surveillance & Perimeter Drift Router.
Manages watchlist targets and computes perimeter drift deltas.
"""

import os
import json
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel, Field

from hamsa.core.monitor import WatchlistManager, ScanDiffEngine
from hamsa.core.models import TargetType
from hamsa.web.deps import GLOBAL_ORCHESTRATOR

router = APIRouter(prefix="/api/watchlist", tags=["Surveillance"])


class WatchlistActionRequest(BaseModel):
    action: str = Field(default="add", pattern="^(add|remove)$")
    value: str = ""
    target: Optional[str] = None  # alias
    target_type: str = "username"
    tags: List[str] = []
    notes: str = ""
    webhook: Optional[str] = None


@router.get("")
async def get_watchlist():
    """Lists all monitored continuous surveillance targets."""
    wm = WatchlistManager()
    return {"watchlist": [t.to_dict() for t in wm.list_all()]}


@router.post("")
async def manage_watchlist(payload: WatchlistActionRequest):
    """Adds or removes a target from the continuous surveillance watchlist."""
    wm = WatchlistManager()
    val = (payload.value or payload.target or "").strip()
    if payload.action == "remove":
        removed = wm.remove(val, target_type=payload.target_type)
        return {"success": removed, "watchlist": [t.to_dict() for t in wm.list_all()]}
    else:
        entry = wm.add(val, target_type=payload.target_type, tags=payload.tags, notes=payload.notes)
        return {"success": True, "entry": entry.to_dict() if entry else None, "watchlist": [t.to_dict() for t in wm.list_all()]}


@router.post("/check")
async def check_watchlist_drift():
    """Executes automated perimeter diff scans across all targets in the watchlist."""
    wm = WatchlistManager()
    items = wm.list_all()
    results = []
    snapshot_dir = os.path.expanduser("~/.hamsa/snapshots")
    os.makedirs(snapshot_dir, exist_ok=True)

    for item in items:
        t_type = TargetType.USERNAME
        if item.target_type == "email":
            t_type = TargetType.EMAIL
        elif item.target_type == "phone":
            t_type = TargetType.PHONE

        tg = await GLOBAL_ORCHESTRATOR.scan([(item.value, t_type)], max_depth=2, recursive=True)
        new_snap = tg.to_dict()
        safe_val = item.value.replace("/", "_")
        snap_file = os.path.join(snapshot_dir, f"{item.target_type}_{safe_val}.json")
        old_snap = {}
        if os.path.exists(snap_file):
            try:
                with open(snap_file, "r", encoding="utf-8") as f:
                    old_snap = json.load(f)
            except Exception:
                pass

        diff = ScanDiffEngine.compute_diff(old_snap, new_snap)
        wm.update_scanned(item.value, item.target_type)
        with open(snap_file, "w", encoding="utf-8") as f:
            json.dump(new_snap, f, indent=2, ensure_ascii=False)

        results.append({
            "target": item.value,
            "type": item.target_type,
            "drift_score": diff.get("drift_score", 0),
            "diff": diff
        })

    return {"status": "checked", "count": len(results), "results": results}

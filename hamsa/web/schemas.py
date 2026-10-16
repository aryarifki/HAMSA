"""
Pydantic Request & Response Validation Schemas for HAMSA Enterprise API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


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


class SpatialFilterRequest(BaseModel):
    case_id: Optional[str] = None
    filter_type: str = Field(default="radius", description="'radius', 'bbox', or 'polygon'")
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    radius_km: Optional[float] = None
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None
    polygon: Optional[List[List[float]]] = None


class TrilaterateRequest(BaseModel):
    p1: List[float] = Field(..., description="[lat, lon] for point 1")
    r1_km: float = Field(..., gt=0, description="Radius 1 in kilometers")
    p2: List[float] = Field(..., description="[lat, lon] for point 2")
    r2_km: float = Field(..., gt=0, description="Radius 2 in kilometers")
    p3: List[float] = Field(..., description="[lat, lon] for point 3")
    r3_km: float = Field(..., gt=0, description="Radius 3 in kilometers")



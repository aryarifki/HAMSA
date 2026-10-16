"""
Knowledge Graph & Forensic Timeline Router.
Provides graph topology retrieval, chronoforensic timeline extraction,
shortest path entity correlation, centrality metrics, and cluster detection.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hamsa.core.database import GLOBAL_DB
from hamsa.core.analytics import (
    GraphAnalyticsEngine,
    SpatialFilterEngine,
    PersonaResolutionEngine,
    RiskScoringEngine,
    ThematicClusteringEngine,
)
from hamsa.web.deps import GLOBAL_ORCHESTRATOR
from hamsa.web.schemas import SpatialFilterRequest, TrilaterateRequest

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph Analytics"])


class ShortestPathRequest(BaseModel):
    case_id: Optional[str] = None
    source_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)


@router.get("")
async def get_graph(case_id: Optional[str] = None):
    """Retrieves the knowledge network graph for a specific case or the global active session."""
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
        if graph.nodes:
            return graph.to_dict()
    return GLOBAL_ORCHESTRATOR.graph.to_dict()


@router.post("/path")
async def find_shortest_path(payload: ShortestPathRequest):
    """Calculates the shortest relational connecting path between two entities in the graph."""
    if payload.case_id:
        graph = await GLOBAL_DB.load_graph(payload.case_id)
    else:
        graph = GLOBAL_ORCHESTRATOR.graph

    result = GraphAnalyticsEngine.find_shortest_path(graph, payload.source_id, payload.target_id)
    return result


@router.get("/centrality")
async def get_graph_centrality(case_id: Optional[str] = None):
    """Calculates Degree Centrality and Bridge Brokerage scores to identify key coordinators."""
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
    else:
        graph = GLOBAL_ORCHESTRATOR.graph

    return GraphAnalyticsEngine.compute_centrality(graph)


@router.get("/clusters")
async def get_graph_clusters(case_id: Optional[str] = None):
    """Decomposes the network into connected component clusters to isolate distinct rings of suspects."""
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
    else:
        graph = GLOBAL_ORCHESTRATOR.graph

    clusters = GraphAnalyticsEngine.detect_clusters(graph)
    return {"clusters": clusters, "total_clusters": len(clusters)}


@router.post("/spatial-filter")
async def apply_spatial_filter(payload: SpatialFilterRequest):
    """
    Filters EXIF photo locations and geographic nodes using spatial computational geometry
    (Haversine Circular Radius, Bounding Box, or Ray-Casting Polygon Geofence).
    """
    if payload.case_id:
        graph = await GLOBAL_DB.load_graph(payload.case_id)
    else:
        graph = GLOBAL_ORCHESTRATOR.graph

    try:
        poly_tuples = None
        if payload.polygon:
            poly_tuples = [(float(p[0]), float(p[1])) for p in payload.polygon]

        result = SpatialFilterEngine.filter_graph_locations(
            graph=graph,
            filter_type=payload.filter_type,
            center_lat=payload.center_lat,
            center_lon=payload.center_lon,
            radius_km=payload.radius_km,
            min_lat=payload.min_lat,
            max_lat=payload.max_lat,
            min_lon=payload.min_lon,
            max_lon=payload.max_lon,
            polygon=poly_tuples,
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Spatial filter computation error: {exc}")


@router.post("/trilaterate")
async def trilaterate_position(payload: TrilaterateRequest):
    """
    Computes estimated GPS coordinate (lat, lon) by trilaterating 3 reference points and circle radii
    (inspired by CCTV people-nearby triangulation).
    """
    try:
        p1 = (float(payload.p1[0]), float(payload.p1[1]))
        p2 = (float(payload.p2[0]), float(payload.p2[1]))
        p3 = (float(payload.p3[0]), float(payload.p3[1]))
        lat, lon = SpatialFilterEngine.trilaterate_coordinates(
            p1=p1, r1_km=payload.r1_km,
            p2=p2, r2_km=payload.r2_km,
            p3=p3, r3_km=payload.r3_km,
        )
        return {
            "estimated_latitude": lat,
            "estimated_longitude": lon,
            "google_maps": f"https://www.google.com/maps?q={lat},{lon}",
            "osm": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Trilateration error: {exc}")


@router.get("/personas")
async def get_persona_clusters(case_id: Optional[str] = None):
    """
    Performs Union-Find Disjoint-Set Persona Resolution to merge fragmented identity nodes into unified personas
    (inspired by nox-framework).
    """
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
    else:
        graph = GLOBAL_ORCHESTRATOR.graph

    personas = PersonaResolutionEngine.resolve_personas(graph)
    return {"personas": personas, "total_personas": len(personas)}


@router.get("/risk-score")
async def get_graph_risk_score(case_id: Optional[str] = None):
    """
    Evaluates compromise severity and generates FAIR-aligned 0-100 risk assessments
    (inspired by nox-framework).
    """
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
    else:
        graph = GLOBAL_ORCHESTRATOR.graph

    return RiskScoringEngine.evaluate_graph_risk(graph)


@router.get("/thematic-clusters")
async def get_thematic_clusters(case_id: Optional[str] = None):
    """
    Performs lightweight semantic topic clustering across graph nodes
    (inspired by carrot2).
    """
    if case_id:
        graph = await GLOBAL_DB.load_graph(case_id)
    else:
        graph = GLOBAL_ORCHESTRATOR.graph

    clusters = ThematicClusteringEngine.cluster_entities(graph)
    return {"thematic_clusters": clusters, "total_themes": len(clusters)}


# Retain alias for timeline at /api/timeline
timeline_router = APIRouter(prefix="/api", tags=["Knowledge Graph Analytics"])

@timeline_router.get("/timeline")
async def get_timeline(case_id: str = "case_default"):
    """Extracts chronological events (EXIF camera timestamps, breach incident dates, malware logs)."""
    events = await GLOBAL_DB.get_timeline_events(case_id)
    return {"case_id": case_id, "events": events}

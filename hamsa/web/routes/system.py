"""
System, Health, Caching & Forensic Reporting Router.
Handles operational health checks, cache operations, community source updates, and report exports.
"""

import os
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from hamsa.core.database import GLOBAL_DB
from hamsa.core.cache import GLOBAL_CACHE
from hamsa.core.sources import SourceManager
from hamsa.core.reporting import ReportGenerator
from hamsa.web.deps import GLOBAL_ORCHESTRATOR

router = APIRouter(prefix="/api", tags=["System & Operations"])


@router.get("/health")
async def health_check():
    """System health check, version, and database connection status."""
    return {
        "status": "online",
        "platform": "HAMSA Enterprise OSINT Suite",
        "version": "2.0.0",
        "database_engine": GLOBAL_DB.engine_type,
        "database_connected": GLOBAL_DB._connected,
        "cache_engine": os.getenv("HAMSA_CACHE_ENGINE", "memory")
    }


@router.get("/cache/stats")
async def cache_stats():
    """Returns L1 Memory LRU and L2 Redis cache metrics."""
    return GLOBAL_CACHE.stats()


@router.post("/cache/clear")
async def cache_clear():
    """Clears L1/L2 cache entries."""
    GLOBAL_CACHE.clear()
    return {"status": "cleared"}


@router.post("/reset")
async def system_reset():
    """Resets active in-memory graphs and flushes cache."""
    GLOBAL_CACHE.clear()
    GLOBAL_ORCHESTRATOR.graph.clear()
    return {"status": "reset", "nodes": 0, "edges": 0}


@router.post("/update-sources")
async def update_sources():
    """Syncs community database definitions (690+ WhatsMyName platforms)."""
    sm = SourceManager()
    count = await sm.update_sources()
    return {"status": "success", "platforms_synced": count}


@router.get("/report")
async def export_report(
    format: str = Query("html", pattern="^(html|markdown)$"),
    case_id: str = "case_default"
):
    """Generates an executive forensic dossier report (HTML printable or Markdown format)."""
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


@router.get("/export")
async def export_graph_data(
    format: str = Query("graphml", pattern="^(graphml|stix|csv_nodes|csv_edges|json)$"),
    case_id: Optional[str] = None
):
    """
    Exports the knowledge network graph into standard enterprise and forensic formats:
    - GraphML: For Gephi, Cytoscape, yEd, and Maltego
    - STIX 2.1: OASIS Cyber Threat Intelligence bundle
    - CSV: Tabular dump of nodes and edges
    - JSON: Native HAMSA graph dictionary
    """
    from fastapi.responses import Response
    from hamsa.core.export import GraphMLExporter, STIX2Exporter, CSVExporter

    graph = await GLOBAL_DB.load_graph(case_id) if case_id else GLOBAL_ORCHESTRATOR.graph

    if format == "graphml":
        xml_data = GraphMLExporter.export(graph)
        return Response(content=xml_data, media_type="application/xml", headers={"Content-Disposition": f"attachment; filename=hamsa_{case_id or 'graph'}.graphml"})
    elif format == "stix":
        stix_data = STIX2Exporter.export(graph)
        return JSONResponse(content=stix_data)
    elif format == "csv_nodes":
        csv_data = CSVExporter.export_nodes_csv(graph)
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=hamsa_{case_id or 'graph'}_nodes.csv"})
    elif format == "csv_edges":
        csv_data = CSVExporter.export_edges_csv(graph)
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=hamsa_{case_id or 'graph'}_edges.csv"})
    else:
        return JSONResponse(content=graph.to_dict())

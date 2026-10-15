"""
HAMSA Enterprise Modular API Routers.
"""

from hamsa.web.routes.auth import router as auth_router
from hamsa.web.routes.cases import router as cases_router
from hamsa.web.routes.scan import router as scan_router
from hamsa.web.routes.graph import router as graph_router, timeline_router
from hamsa.web.routes.surveillance import router as surveillance_router
from hamsa.web.routes.system import router as system_router

__all__ = [
    "auth_router",
    "cases_router",
    "scan_router",
    "graph_router",
    "timeline_router",
    "surveillance_router",
    "system_router",
]

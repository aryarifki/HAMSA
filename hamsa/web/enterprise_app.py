"""
HAMSA Enterprise ASGI Application
High-performance async web service built on FastAPI and Uvicorn.
Uses modular, domain-driven routing architecture for maximum maintainability.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hamsa.core.database import GLOBAL_DB
from hamsa.utils.formatters import log_info, log_success
from hamsa.web.routes import (
    auth_router,
    cases_router,
    scan_router,
    graph_router,
    timeline_router,
    surveillance_router,
    system_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and graceful shutdown lifecycles."""
    log_info("Starting HAMSA Enterprise Intelligence Service...")
    await GLOBAL_DB.connect()
    yield
    log_info("Shutting down HAMSA Enterprise Intelligence Service...")
    await GLOBAL_DB.close()


def create_app() -> FastAPI:
    """Application factory for HAMSA Enterprise API."""
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

    # --------------------------------------------------------------------------
    # Register Modular Domain Routers
    # --------------------------------------------------------------------------
    app.include_router(auth_router)
    app.include_router(system_router)
    app.include_router(cases_router)
    app.include_router(scan_router)
    app.include_router(graph_router)
    app.include_router(timeline_router)
    app.include_router(surveillance_router)

    return app


# Root application instance for Uvicorn ASGI server
app = create_app()

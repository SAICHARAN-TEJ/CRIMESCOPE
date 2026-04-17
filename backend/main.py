"""
CRIMESCOPE v2 — FastAPI application factory.

Creates and configures the FastAPI app with:
- CORS middleware
- All API routers
- Startup/shutdown lifecycle hooks
- Structured logging
"""

from __future__ import annotations

import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import structlog

from core.config import get_settings
from core.logger import setup_logging
from core.state import load_all_simulations
from memory.zep_manager import get_memory_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown hooks."""
    log = structlog.get_logger("crimescope.app")

    # ── STARTUP ──────────────────────────────────────────────
    settings = get_settings()

    # Validate configuration
    errors = settings.validate_required()
    if errors:
        for err in errors:
            log.error("config_error", detail=err)
        log.warning("starting_with_config_warnings", errors=len(errors))

    # Hydrate simulation state from disk
    await load_all_simulations()

    log.info(
        "startup_complete",
        host=settings.host,
        port=settings.port,
        llm_model=settings.llm_model_name,
        zep=bool(settings.zep_api_key),
    )

    yield

    # ── SHUTDOWN ─────────────────────────────────────────────
    # Flush remaining Zep writes
    mem = get_memory_manager()
    await mem.close()
    log.info("shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the CRIMESCOPE FastAPI application."""

    # Force UTF-8 on Windows
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Initialize structured logging
    setup_logging()

    settings = get_settings()

    app = FastAPI(
        title="CRIMESCOPE API",
        description="Crime prediction & multi-agent swarm simulation engine",
        version="2.0.0",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────────
    from api.health import router as health_router
    from api.simulation import router as sim_router, list_router
    from api.events import router as events_router
    from api.chat import router as chat_router

    app.include_router(health_router)
    app.include_router(sim_router)
    app.include_router(list_router)
    app.include_router(events_router)
    app.include_router(chat_router)

    return app

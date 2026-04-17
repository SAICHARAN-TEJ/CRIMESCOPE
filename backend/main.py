"""
CrimeScope API — FastAPI application entry point.

Start with:  uvicorn backend.main:app --reload --port 5001
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings, Settings
from backend.utils.logger import get_logger

logger = get_logger("crimescope.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle — resilient to missing services."""
    # ── Startup banner ────────────────────────────────────────────────
    logger.info("=" * 50)
    logger.info("  CrimeScope Swarm Intelligence Engine v1.3.0")
    logger.info("=" * 50)

    # Validate config
    warnings = Settings.validate_config(settings)
    if warnings:
        for w in warnings:
            logger.warning(f"  ⚠ {w}")
        logger.info("  → Running in DEMO mode (external services unavailable)")
    else:
        logger.info("  ✓ All services configured")

    # Neo4j — optional, don't crash if unavailable
    neo4j_ok = False
    try:
        from backend.graph.neo4j_client import neo4j_client
        await neo4j_client.connect()
        neo4j_ok = True
        logger.info("  ✓ Neo4j connected")
    except Exception as e:
        logger.warning(f"  ⚠ Neo4j unavailable: {e} — graph queries will use demo data")

    logger.info("=" * 50)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    if neo4j_ok:
        try:
            from backend.graph.neo4j_client import neo4j_client
            await neo4j_client.close()
            logger.info("✓ Neo4j disconnected")
        except Exception:
            pass
    logger.info("CrimeScope shutdown complete")


app = FastAPI(
    title="CrimeScope API",
    version="1.3.0",
    description="Multi-agent swarm intelligence engine for criminal reconstruction.",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────
from backend.routers import cases, chat, demo, graph, report, simulation, upload

app.include_router(cases.router, prefix="/api/v1", tags=["Cases"])
app.include_router(simulation.router, prefix="/api/v1", tags=["Simulation"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])
app.include_router(report.router, prefix="/api/v1", tags=["Report"])
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(demo.router, prefix="/api/v1", tags=["Demo"])


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "mode": "demo" if settings.is_demo_mode else "live",
        "ts": time.time(),
        "agents": settings.swarm_agent_count,
    }

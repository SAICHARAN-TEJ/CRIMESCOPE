# SPDX-License-Identifier: AGPL-3.0-only
"""
CrimeScope API v2.0 — FastAPI application entry point.

Production-ready with:
  - Redis cache + pub/sub lifecycle
  - Neo4j + in-memory graph fallback
  - Structured startup/shutdown
  - Health check endpoint

Start with:  uvicorn backend.main:app --reload --port 5001
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings, Settings
from backend.core.exceptions import CrimeScopeError, CaseNotFoundError
from backend.utils.logger import get_logger

logger = get_logger("crimescope.main")

_STARTUP_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle — resilient to missing services."""
    global _STARTUP_TIME
    _STARTUP_TIME = time.time()

    # ── Startup banner ────────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info("  CrimeScope Swarm Intelligence Engine v2.0.0")
    logger.info("  Production SaaS MVP — GraphRAG + Parallel Agents")
    logger.info("=" * 55)

    # Validate config
    warnings = Settings.validate_config(settings)
    if warnings:
        for w in warnings:
            logger.warning(f"  ⚠ {w}")
        logger.info("  → Running in DEMO mode (external services unavailable)")
    else:
        logger.info("  ✓ All services configured")

    # ── Redis ─────────────────────────────────────────────────────────
    try:
        from backend.infrastructure.redis_client import redis_cache
        await redis_cache.connect(settings.redis_url)
        if redis_cache.is_connected:
            logger.info("  ✓ Redis connected (cache + pub/sub active)")
        else:
            logger.info("  ✓ Cache active (in-memory mode — Redis not required)")
    except Exception as e:
        logger.warning(f"  ⚠ Redis init failed: {e} — using in-memory cache")

    # ── Neo4j ─────────────────────────────────────────────────────────
    neo4j_ok = False
    try:
        from backend.graph.neo4j_client import neo4j_client
        await neo4j_client.connect()
        neo4j_ok = neo4j_client.is_connected
        if neo4j_ok:
            logger.info("  ✓ Neo4j connected (server mode)")
        else:
            logger.info("  ✓ Graph store active (in-memory mode — Neo4j not required)")
    except Exception as e:
        logger.warning(f"  ⚠ Graph init failed: {e} — graph queries will use demo data")

    logger.info("=" * 55)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    # Redis
    try:
        from backend.infrastructure.redis_client import redis_cache
        await redis_cache.close()
        logger.info("✓ Redis disconnected")
    except Exception:
        pass

    # Neo4j
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
    version="2.0.0",
    description="Multi-agent swarm intelligence engine with GraphRAG for criminal reconstruction.",
    lifespan=lifespan,
)


# ── Exception Handlers ───────────────────────────────────────────────────

@app.exception_handler(CaseNotFoundError)
async def case_not_found_handler(request: Request, exc: CaseNotFoundError):
    return JSONResponse(status_code=404, content={"error": str(exc), "case_id": exc.case_id})


@app.exception_handler(CrimeScopeError)
async def crimescope_error_handler(request: Request, exc: CrimeScopeError):
    status = 503 if exc.retryable else 500
    return JSONResponse(
        status_code=status,
        content={"error": str(exc), "detail": exc.detail, "retryable": exc.retryable},
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
from backend.routers import health as health_router

app.include_router(health_router.router, prefix="/api/v1", tags=["Health"])
app.include_router(cases.router, prefix="/api/v1", tags=["Cases"])
app.include_router(simulation.router, prefix="/api/v1", tags=["Simulation"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])
app.include_router(report.router, prefix="/api/v1", tags=["Report"])
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(demo.router, prefix="/api/v1", tags=["Demo"])

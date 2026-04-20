"""
CrimeScope API v4.0 — FastAPI Application Entry Point.

Production-ready with:
  - JWT authentication on all routes + WebSocket
  - Redis pub/sub for real-time agent event streaming
  - Neo4j with idempotent MERGE writes
  - MinIO pre-signed URLs for direct uploads
  - Circuit breakers on all external service calls
  - Structured JSON logging with correlation IDs
  - ProcessPoolExecutor for CPU-bound video processing

Start: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logger import get_logger, setup_logging
from app.core.redis_client import get_redis
from app.graph.driver import get_neo4j
from app.storage.minio_client import get_minio


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifecycle — connect/disconnect all services."""
    setup_logging("INFO")
    logger = get_logger("crimescope.main")

    settings = get_settings()

    logger.info("=" * 60)
    logger.info("  CrimeScope — Swarm Intelligence Engine v4.0.0")
    logger.info("  Production SaaS — Zero-Trust + Real-Time Streaming")
    logger.info("=" * 60)

    # ── Startup: connect services ────────────────────────────────────
    redis = get_redis()
    await redis.connect()

    neo4j = get_neo4j()
    await neo4j.connect()

    minio = get_minio()
    minio.connect()

    logger.info(
        f"Services: Redis={'✓' if redis.connected else '✗'} "
        f"Neo4j={'✓' if neo4j.connected else '✗'} "
        f"MinIO={'✓' if minio.connected else '✗'}"
    )
    logger.info("CrimeScope API ready")

    yield

    # ── Shutdown: disconnect services ────────────────────────────────
    logger.info("Shutting down...")
    await redis.disconnect()
    await neo4j.disconnect()
    logger.info("CrimeScope stopped")


# ── Application ──────────────────────────────────────────────────────────

app = FastAPI(
    title="CrimeScope API",
    version="4.0.0",
    description=(
        "Production-grade criminal reconstruction engine. "
        "JWT auth, parallel AI agents, Neo4j knowledge graph, "
        "real-time WebSocket streaming via Redis pub/sub."
    ),
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────

from app.api.router import router as api_router
from app.api.websocket import router as ws_router

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)

# SPDX-License-Identifier: AGPL-3.0-only
"""Health check endpoint — detailed service status for monitoring."""

import time
from typing import Any, Dict

from fastapi import APIRouter

from backend.config import settings
from backend.utils.logger import get_logger

router = APIRouter()
logger = get_logger("crimescope.health")


@router.get("/health")
async def health_check():
    """
    Detailed health check for all backend services.

    Returns:
        {
            "status": "healthy|degraded|unhealthy",
            "uptime_seconds": 123.4,
            "services": {
                "neo4j": {"status": "connected|fallback|error", ...},
                "redis": {"status": "connected|in-memory|error", ...},
                "chromadb": {"status": "connected|unavailable", ...},
                "openrouter": {"status": "available|error", ...},
                "supabase": {"status": "connected|unavailable", ...},
            },
            "version": "2.0.0"
        }
    """
    services: Dict[str, Any] = {}
    healthy_count = 0
    total_count = 5

    # ── Neo4j ────────────────────────────────────────────────────────
    try:
        from backend.graph.neo4j_client import neo4j_client
        if neo4j_client._driver:
            start = time.time()
            async with neo4j_client._driver.session() as s:
                await s.run("RETURN 1")
            latency = round((time.time() - start) * 1000, 1)
            services["neo4j"] = {"status": "connected", "latency_ms": latency}
            healthy_count += 1
        elif neo4j_client._mem is not None:
            node_count = sum(len(v) for v in neo4j_client._mem._nodes.values())
            services["neo4j"] = {"status": "fallback", "mode": "in-memory", "nodes": node_count}
            healthy_count += 1
        else:
            services["neo4j"] = {"status": "unavailable"}
    except Exception as e:
        services["neo4j"] = {"status": "error", "error": str(e)[:200]}

    # ── Redis ────────────────────────────────────────────────────────
    try:
        from backend.infrastructure.redis_client import redis_cache
        services["redis"] = await redis_cache.health()
        if services["redis"].get("status") in ("connected", "in-memory"):
            healthy_count += 1
    except Exception as e:
        services["redis"] = {"status": "error", "error": str(e)[:200]}

    # ── ChromaDB ─────────────────────────────────────────────────────
    try:
        from backend.memory.chroma_client import memory_client
        if memory_client._client:
            collections = memory_client._client.count_collections()
            services["chromadb"] = {"status": "connected", "collections": collections}
            healthy_count += 1
        else:
            services["chromadb"] = {"status": "unavailable"}
    except Exception as e:
        services["chromadb"] = {"status": "error", "error": str(e)[:200]}

    # ── OpenRouter ───────────────────────────────────────────────────
    try:
        from backend.utils.openrouter import openrouter
        models = [settings.fast_model_name, settings.reasoning_model_name, settings.synthesis_model_name]
        services["openrouter"] = {
            "status": "configured",
            "models": len(set(models)),
            "model_names": list(set(models)),
        }
        if settings.openrouter_api_key:
            services["openrouter"]["status"] = "available"
            healthy_count += 1
        else:
            services["openrouter"]["status"] = "no_api_key"
    except Exception as e:
        services["openrouter"] = {"status": "error", "error": str(e)[:200]}

    # ── Supabase ─────────────────────────────────────────────────────
    try:
        from backend.db.supabase_client import get_supabase
        client = get_supabase()
        if client:
            services["supabase"] = {"status": "connected"}
            healthy_count += 1
        else:
            services["supabase"] = {"status": "unavailable", "mode": "in-memory fallback"}
    except Exception as e:
        services["supabase"] = {"status": "error", "error": str(e)[:200]}

    # ── Overall status ───────────────────────────────────────────────
    if healthy_count >= 4:
        status = "healthy"
    elif healthy_count >= 2:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "services": services,
        "healthy_services": healthy_count,
        "total_services": total_count,
        "version": "2.0.0",
        "agent_count": settings.num_agents,
        "max_rounds": settings.max_rounds,
    }


@router.get("/health/ping")
async def ping():
    """Lightweight liveness probe."""
    return {"status": "ok"}

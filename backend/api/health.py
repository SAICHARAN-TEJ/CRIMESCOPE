"""
CRIMESCOPE v2 — Health and system API routes.

GET /health — liveness check
GET /api/system/info — system metadata
"""

from __future__ import annotations

import time

from fastapi import APIRouter

from core.config import get_settings
from models.schemas import HealthResponse

_START_TIME = time.time()

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness probe."""
    return HealthResponse(
        status="ok",
        service="CRIMESCOPE Backend v2",
        uptime_s=round(time.time() - _START_TIME, 1),
    )


@router.get("/api/system/info")
async def system_info():
    """System metadata."""
    settings = get_settings()
    return {
        "service": "CRIMESCOPE Backend v2",
        "llm_model": settings.llm_model_name,
        "llm_base_url": settings.llm_base_url,
        "boost_available": settings.boost_available,
        "zep_configured": bool(settings.zep_api_key),
        "uptime_s": round(time.time() - _START_TIME, 1),
    }

"""
CrimeScope — REST API Router.

All endpoints require JWT authentication and rate limiting.
Uploads go directly to MinIO via pre-signed URLs — backend never streams large files.

Endpoints:
  POST /auth/token          — Login and get JWT
  POST /upload/presign      — Get pre-signed MinIO URL
  POST /analysis/start      — Start analysis pipeline
  GET  /analysis/{job_id}   — Get job status/results
  GET  /graph/{job_id}      — Get Neo4j subgraph
  GET  /healthz             — Health check (no auth)
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.dependencies import inject_correlation_id, rate_limit, require_auth
from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.core.security import create_access_token, hash_password, verify_password
from app.engine.supervisor import Supervisor
from app.graph.driver import get_neo4j
from app.schemas.events import (
    AnalysisStartRequest,
    HealthResponse,
    JobResponse,
    JobStatus,
    LoginRequest,
    PresignedURLResponse,
    TokenResponse,
    UploadInitRequest,
)
from app.storage.minio_client import get_minio

router = APIRouter()
logger = get_logger("crimescope.api")

# In-memory user store (replace with DB in production)
_USERS: dict[str, dict[str, str]] = {
    "admin": {"password_hash": hash_password("crimescope"), "user_id": "admin"},
}

# In-memory job store
_JOBS: dict[str, dict[str, Any]] = {}


# ── Auth ──────────────────────────────────────────────────────────────────


@router.post("/auth/token", response_model=TokenResponse, tags=["Auth"])
async def login(req: LoginRequest, _: None = Depends(rate_limit)):
    """Authenticate and return a JWT access token."""
    user = _USERS.get(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    from app.core.config import get_settings
    settings = get_settings()
    token = create_access_token({"sub": user["user_id"], "username": req.username})
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


# ── Upload ────────────────────────────────────────────────────────────────


@router.post("/upload/presign", response_model=PresignedURLResponse, tags=["Upload"])
async def get_presigned_url(
    req: UploadInitRequest,
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
    _cid: str = Depends(inject_correlation_id),
):
    """
    Get a pre-signed URL for direct-to-MinIO upload.
    Frontend uploads the file directly — backend never touches the bytes.
    """
    import uuid
    user_id = user.get("sub", "anon")
    object_key = f"uploads/{user_id}/{uuid.uuid4().hex}/{req.filename}"

    minio = get_minio()
    url = minio.generate_presigned_put(object_key, req.content_type)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable",
        )
    return PresignedURLResponse(upload_url=url, object_key=object_key)


# ── Analysis ──────────────────────────────────────────────────────────────


@router.post("/analysis/start", response_model=JobResponse, tags=["Analysis"])
async def start_analysis(
    req: AnalysisStartRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
    _cid: str = Depends(inject_correlation_id),
):
    """
    Start a new analysis pipeline.
    Returns immediately with job_id and WebSocket URL.
    Pipeline runs in the background.
    """
    job_id = req.job_id
    user_id = user.get("sub", "anon")

    # Store job metadata
    _JOBS[job_id] = {
        "user_id": user_id,
        "status": JobStatus.QUEUED,
        "files": [f.model_dump() for f in req.files],
        "question": req.question,
        "result": None,
    }

    # Run pipeline in background
    files_data = [f.model_dump() for f in req.files]
    background_tasks.add_task(_run_pipeline, job_id, user_id, files_data, req.question)

    logger.info(f"Job {job_id} queued for {user_id} ({len(req.files)} files)")

    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        ws_url=f"/ws/analysis/{job_id}",
    )


@router.get("/analysis/{job_id}", tags=["Analysis"])
async def get_job_status(
    job_id: str,
    user: dict = Depends(require_auth),
):
    """Get the current status and results of an analysis job."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ownership check
    from app.api.dependencies import verify_job_ownership
    verify_job_ownership(user, job["user_id"])

    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job.get("result"),
    }


# ── Graph ─────────────────────────────────────────────────────────────────


@router.get("/graph/{job_id}", tags=["Graph"])
async def get_graph(
    job_id: str,
    user: dict = Depends(require_auth),
):
    """Get the Neo4j knowledge graph for a job."""
    job = _JOBS.get(job_id)
    if job:
        from app.api.dependencies import verify_job_ownership
        verify_job_ownership(user, job["user_id"])

    neo4j = get_neo4j()
    subgraph = await neo4j.get_subgraph(job_id)
    return subgraph


# ── Health ────────────────────────────────────────────────────────────────


@router.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """System health check — no authentication required."""
    redis = get_redis()
    neo4j = get_neo4j()
    minio = get_minio()

    redis_health, neo4j_health = await asyncio.gather(
        redis.health(),
        neo4j.health(),
    )
    minio_health = minio.health()

    services = {
        "redis": redis_health,
        "neo4j": neo4j_health,
        "minio": minio_health,
    }

    all_ok = all(s.get("status") == "ok" for s in services.values())
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        services=services,
    )


# ── Background pipeline runner ────────────────────────────────────────────


async def _run_pipeline(
    job_id: str,
    user_id: str,
    files: list[dict],
    question: str,
) -> None:
    """Run the supervisor pipeline in the background."""
    _JOBS[job_id]["status"] = JobStatus.PROCESSING

    try:
        supervisor = Supervisor()
        result = await supervisor.run(job_id, files, question)
        _JOBS[job_id]["status"] = result.status
        _JOBS[job_id]["result"] = result.model_dump()
    except Exception as e:
        logger.error(f"Pipeline {job_id} failed: {e}", exc_info=True)
        _JOBS[job_id]["status"] = JobStatus.FAILED
        _JOBS[job_id]["result"] = {"error": str(e)}

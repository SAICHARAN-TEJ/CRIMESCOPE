"""
CrimeScope â€” REST API Router.

All endpoints require JWT authentication and rate limiting.
Uploads go directly to MinIO via pre-signed URLs â€” backend never streams large files.

Endpoints:
  POST /auth/token          â€” Login and get JWT
  POST /upload/presign      â€” Get pre-signed MinIO URL
  POST /analysis/start      â€” Start analysis pipeline
  GET  /analysis/{job_id}   â€” Get job status/results
  GET  /graph/{job_id}      â€” Get Neo4j subgraph
  GET  /healthz             â€” Health check (no auth)
  GET  /personas            â€” List active personas for a job
  POST /chat                â€” Send a question to the ReportAgent
  POST /scenario            â€” Inject a scenario hypothesis
  GET  /scenario/{id}       â€” Get scenario evaluation results
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import text

from app.api.dependencies import inject_correlation_id, rate_limit, require_auth
from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.core.security import create_access_token, hash_password, sanitize_input, verify_password
from app.db import repositories
from app.db.models import Job, Scenario
from app.engine.supervisor import Supervisor
from app.graph.driver import get_neo4j
from app.schemas.events import (
    AnalysisStartRequest,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    JobResponse,
    JobStatus,
    LoginRequest,
    PersonaMaterializeResponse,
    PersonaMaterialized,
    PresignedURLResponse,
    ScenarioRequest,
    ScenarioResult,
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


def _job_to_dict(job: Job) -> dict[str, Any]:
    """Serialize a Job ORM row to the API-facing dict shape."""
    return {
        "user_id": job.user_id,
        "status": job.status,
        "files": job.source_files,
        "question": job.question,
        "result": job.result_summary,
        "error_message": job.error_message,
    }


def _scenario_to_dict(scenario: Scenario) -> dict[str, Any]:
    """Serialize a Scenario ORM row to the API-facing dict shape."""
    return {
        "job_id": scenario.job_id,
        "hypothesis": scenario.hypothesis,
        "status": scenario.status,
        "result": scenario.diff_result,
    }


async def _interview_persona(
    job_id: str,
    persona_id: str,
    message: str,
    graph_context: dict[str, Any] | None,
) -> tuple[Any, str, list[str], float]:
    """
    Run one message against a materialized graph-entity persona.
    Returns (result, reply_text, sources, confidence).
    """
    from app.engine.agents.persona import materialize_graph_personas

    graph_context = graph_context or {"nodes": [], "edges": []}
    agents = materialize_graph_personas(graph_context)
    agent = next((a for a in agents if a.node_id == persona_id), None)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Persona {persona_id} not found in job {job_id} graph",
        )

    result = await agent.run(job_id, {"message": message})
    reply = ""
    sources: list[str] = []
    if result.success and result.entities:
        payload = result.entities[0] if result.entities else {}
        reply = payload.get("message", "")
        sources = payload.get("evidence_refs", [])

    return result, reply, sources, 1.0 if result.success else 0.0


# â”€â”€ Auth â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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


# â”€â”€ Upload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.post("/upload/presign", response_model=PresignedURLResponse, tags=["Upload"])
async def get_presigned_url(
    req: UploadInitRequest,
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
    _cid: str = Depends(inject_correlation_id),
):
    """
    Get a pre-signed URL for direct-to-MinIO upload.
    Frontend uploads the file directly â€” backend never touches the bytes.
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


# â”€â”€ Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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

    # Persist job metadata in Postgres (queued). Create is enqueued to the
    # DLQ on DB failure rather than crashing the request.
    files_data = [f.model_dump() for f in req.files]
    await repositories.jobs.create(job_id, user_id, files_data, question=req.question)

    # Run pipeline in background
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
    job = await repositories.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Ownership check
    from app.api.dependencies import verify_job_ownership
    verify_job_ownership(user, job.user_id)

    return {
        "job_id": job_id,
        "status": job.status,
        "result": job.result_summary,
    }


@router.post("/analysis/{job_id}/retry", response_model=JobResponse, tags=["Analysis"])
async def retry_analysis(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
    _cid: str = Depends(inject_correlation_id),
):
    """Re-queue a failed analysis job. Runs the pipeline again in the background."""
    job = await repositories.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.api.dependencies import verify_job_ownership
    verify_job_ownership(user, job.user_id)

    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=409,
            detail=f"Job is {job.status}; only failed jobs can be retried",
        )

    files_data = job.source_files
    question = job.question
    await repositories.jobs.update_status(job_id, JobStatus.QUEUED.value, result_summary=None)
    background_tasks.add_task(_run_pipeline, job_id, job.user_id, files_data, question)

    logger.info(f"Job {job_id} re-queued for retry")
    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        ws_url=f"/ws/analysis/{job_id}",
    )


# â”€â”€ Graph â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/graph/{job_id}", tags=["Graph"])
async def get_graph(
    job_id: str,
    user: dict = Depends(require_auth),
):
    """Get the Neo4j knowledge graph for a job."""
    job = await repositories.jobs.get(job_id)
    if job:
        from app.api.dependencies import verify_job_ownership
        verify_job_ownership(user, job.user_id)

    neo4j = get_neo4j()
    subgraph = await neo4j.get_subgraph(job_id)
    return subgraph


# â”€â”€ Personas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/personas", tags=["Swarm Intelligence"])
async def list_personas(
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
):
    """List the active investigative personas and their configurations."""
    from app.engine.agents.persona import get_default_personas

    personas = get_default_personas()
    return {
        "personas": [
            {
                "name": p.name,
                "role": p.role,
                "expertise_tags": p.expertise_tags,
                "temperature": p.temperature,
            }
            for p in personas
        ],
        "count": len(personas),
    }


@router.post(
    "/analysis/{job_id}/personas",
    response_model=PersonaMaterializeResponse,
    tags=["Swarm Intelligence"],
)
async def materialize_personas(
    job_id: str,
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
    _cid: str = Depends(inject_correlation_id),
):
    """
    Materialize conversational persona agents from the job's Neo4j Person
    nodes. Each persona is grounded ONLY in its node's stored facts and
    edges — never invented outside the case data. Responses cite node IDs.
    """
    job = await repositories.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.api.dependencies import verify_job_ownership
    verify_job_ownership(user, job.user_id)

    from app.core.config import get_settings
    from app.engine.agents.persona import materialize_graph_personas

    settings = get_settings()
    neo4j = get_neo4j()
    subgraph = await neo4j.get_subgraph(job_id)

    persona_agents = materialize_graph_personas(subgraph, max_personas=settings.max_personas)

    found_statements = []
    for node in subgraph.get("nodes", []):
        props = node.get("props", {})
        statement = props.get("statement") or props.get("testimony") or props.get("quote")
        if statement:
            found_statements.append(str(statement))

    return PersonaMaterializeResponse(
        job_id=job_id,
        personas=[
            PersonaMaterialized(
                persona_id=p.node_id,
                name=p.person_name,
                role=p.role_hint,
                evidence_refs=p._evidence_refs(),
                grounded_nodes=len(set(p._evidence_refs())),
                statements=found_statements,
            )
            for p in persona_agents
        ],
        count=len(persona_agents),
        total_person_nodes=sum(
            1 for n in subgraph.get("nodes", []) if "Person" in str(n.get("type", ""))
        ),
    )


# â”€â”€ Chat (ReportAgent) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.post("/chat", response_model=ChatResponse, tags=["Swarm Intelligence"])
async def send_chat(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
    _cid: str = Depends(inject_correlation_id),
):
    """
    Send an investigation question to the ReportAgent.
    The agent queries the full knowledge graph and returns an analysis.
    Streaming updates arrive via REPORT_CHUNK WebSocket events.
    """
    job = await repositories.jobs.get(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.api.dependencies import verify_job_ownership
    verify_job_ownership(user, job.user_id)

    # Sanitize the message
    sanitized_message = sanitize_input(req.message)
    if not sanitized_message.strip():
        raise HTTPException(status_code=400, detail="Empty message after sanitization")

    # Get or create conversation (persisted in Postgres)
    conv_id = req.conversation_id or f"conv-{uuid4().hex[:12]}"
    await repositories.conversations.ensure(conv_id, req.job_id)

    # Load persisted history for LLM context
    conversation_history = await repositories.conversations.history(conv_id)

    # Get graph context for the report agent
    neo4j = get_neo4j()
    graph_context = await neo4j.get_subgraph(req.job_id)

    # Get entities from the job result
    entities = []
    if job.result_summary and isinstance(job.result_summary, dict):
        for agent_result in job.result_summary.get("agents", []):
            if isinstance(agent_result, dict):
                entities.extend(agent_result.get("entities", []))

    # Persist user message (best-effort — never blocks the response)
    await repositories.conversations.add_message(conv_id, "user", sanitized_message)

    # ── Persona interview vs. ReportAgent ───────────────────────────
    if req.persona_id:
        result, report_text, sources, confidence = await _interview_persona(
            req.job_id, req.persona_id, sanitized_message, graph_context
        )
    else:
        from app.engine.agents.report import ReportAgent

        report_agent = ReportAgent()
        payload = {
            "message": sanitized_message,
            "conversation_history": conversation_history,
            "graph_context": graph_context,
            "entities": entities,
            "text_chunks": [],
        }
        result = await report_agent.run(req.job_id, payload)

        # Extract report from result
        report_text = ""
        sources = []
        confidence = 0.0
        if result.success and result.entities:
            report_data = result.entities[0] if result.entities else {}
            report_text = report_data.get("report", "")
            sources = report_data.get("sources", [])
            confidence = report_data.get("confidence", 0.0)

    # Persist assistant message (best-effort — never blocks the response)
    await repositories.conversations.add_message(conv_id, "agent", report_text, citations=sources)

    return ChatResponse(
        conversation_id=conv_id,
        message=report_text,
        sources=sources,
        confidence=confidence,
        persona_id=req.persona_id,
    )


# â”€â”€ Scenario Injection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.post("/scenario", tags=["Swarm Intelligence"])
async def inject_scenario(
    req: ScenarioRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth),
    _rate: None = Depends(rate_limit),
    _cid: str = Depends(inject_correlation_id),
):
    """
    Inject a "what-if" hypothesis for evaluation by all personas.
    Returns immediately with scenario_id. Results arrive via WebSocket events.
    """
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.scenario_enabled:
        raise HTTPException(status_code=403, detail="Scenario injection is disabled")

    job = await repositories.jobs.get(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.api.dependencies import verify_job_ownership
    verify_job_ownership(user, job.user_id)

    sanitized_hypothesis = sanitize_input(req.hypothesis)
    if not sanitized_hypothesis.strip():
        raise HTTPException(status_code=400, detail="Empty hypothesis after sanitization")

    scenario_id = f"scenario-{uuid4().hex[:12]}"

    # Get entities from the job result
    entities = []
    if job.result_summary and isinstance(job.result_summary, dict):
        for agent_result in job.result_summary.get("agents", []):
            if isinstance(agent_result, dict):
                entities.extend(agent_result.get("entities", []))

    # Persist scenario metadata (Postgres, safe on DLQ)
    await repositories.scenarios.create(
        scenario_id,
        req.job_id,
        {"hypothesis": sanitized_hypothesis},
        status="pending",
    )

    # Run scenario agent in background
    background_tasks.add_task(
        _run_scenario, scenario_id, req.job_id, sanitized_hypothesis, entities
    )

    return {
        "scenario_id": scenario_id,
        "hypothesis": sanitized_hypothesis,
        "status": "pending",
    }


@router.get("/scenario/{scenario_id}", tags=["Swarm Intelligence"])
async def get_scenario_result(
    scenario_id: str,
    user: dict = Depends(require_auth),
):
    """Get the evaluation results of a previously injected scenario."""
    scenario = await repositories.scenarios.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Verify the user owns the associated job
    job = await repositories.jobs.get(scenario.job_id)
    if job:
        from app.api.dependencies import verify_job_ownership
        verify_job_ownership(user, job.user_id)

    return _scenario_to_dict(scenario)


# â”€â”€ Health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """System health check â€” no authentication required."""
    redis = get_redis()
    neo4j = get_neo4j()
    minio = get_minio()

    redis_health, neo4j_health = await asyncio.gather(
        redis.health(),
        neo4j.health(),
    )
    minio_health = minio.health()

    # Postgres liveness probe
    postgres_health = {"status": "degraded"}
    try:
        from app.db.session import engine as _db_engine

        async with _db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres_health = {"status": "ok"}
    except Exception as e:
        logger.warning(f"Postgres health check failed: {e}")

    services = {
        "redis": redis_health,
        "neo4j": neo4j_health,
        "minio": minio_health,
        "postgres": postgres_health,
    }

    all_ok = all(s.get("status") == "ok" for s in services.values())
    if not all_ok:
        # Compose healthchecks (curl -f) must see a failing dependency as
        # unhealthy, otherwise the app starts serving 5xx traffic.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "degraded", "services": services},
        )
    return HealthResponse(
        status="healthy",
        services=services,
    )


# â”€â”€ Background runners â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def _run_pipeline(
    job_id: str,
    user_id: str,
    files: list[dict],
    question: str,
) -> None:
    """Run the supervisor pipeline in the background."""
    await repositories.jobs.update_status(job_id, JobStatus.PROCESSING.value)

    try:
        supervisor = Supervisor()
        result = await supervisor.run(job_id, files, question)
        await repositories.jobs.update_status(
            job_id, result.status.value, result_summary=result.model_dump()
        )
    except Exception as e:
        logger.error(f"Pipeline {job_id} failed: {e}", exc_info=True)
        await repositories.jobs.update_status(
            job_id, JobStatus.FAILED.value, error_message=str(e)
        )


async def _run_scenario(
    scenario_id: str,
    job_id: str,
    hypothesis: str,
    entities: list[dict],
) -> None:
    """Run scenario evaluation in the background."""
    from app.engine.agents.scenario import ScenarioAgent

    try:
        agent = ScenarioAgent()
        result = await agent.run(job_id, {
            "hypothesis": hypothesis,
            "entities": entities,
            "text_chunks": [],
        })

        await repositories.scenarios.update_result(
            scenario_id,
            "completed" if result.success else "failed",
            diff_result={
                "success": result.success,
                "facts": result.facts,
                "entities": result.entities,
                "error": result.error,
            },
        )
    except Exception as e:
        logger.error(f"Scenario {scenario_id} failed: {e}", exc_info=True)
        await repositories.scenarios.update_result(
            scenario_id, "failed", diff_result={"error": str(e)}
        )


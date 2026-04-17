"""
CRIMESCOPE v2 — Simulation API routes.

Covers:
- POST /api/simulation/start — launch a new simulation
- GET  /api/simulation/{id}/status — get simulation status
- GET  /api/simulation/{id}/agents — get all agents
- GET  /api/simulation/{id}/feed — get platform feed
- GET  /api/simulation/{id}/graph — get knowledge graph
- GET  /api/simulation/{id}/report — get prediction report
- GET  /api/simulations — list all simulations
- POST /api/simulation/{id}/inject — inject variable (God Mode)
"""

from __future__ import annotations

import uuid
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

import structlog
import aiofiles

from core.config import get_settings
from core.state import (
    SimulationState, FeedItem,
    get_simulation, set_simulation, list_simulations,
)
from models.schemas import (
    SimulationStartResponse, SimulationStatusResponse,
    AgentResponse, PostResponse, GraphResponse, ReportResponse,
    SimulationSummaryResponse, InjectVariableRequest,
)
from simulation.runner import run_simulation_pipeline
from simulation.events import get_event_bus

log = structlog.get_logger("crimescope.api.simulation")

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


# ── POST /start ──────────────────────────────────────────────

@router.post("/start", response_model=SimulationStartResponse)
async def start_simulation(
    background_tasks: BackgroundTasks,
    requirement: str = Form(...),
    agent_count: int = Form(default=50),
    max_rounds: int = Form(default=25),
    platform: str = Form(default="parallel"),
    files: list[UploadFile] = File(default=[]),
):
    """Start a new simulation pipeline."""
    settings = get_settings()
    sim_id = str(uuid.uuid4())

    # Validate
    if len(requirement) < 10:
        raise HTTPException(400, "Requirement must be at least 10 characters")
    if not (5 <= agent_count <= 500):
        raise HTTPException(400, "Agent count must be between 5 and 500")
    if not (1 <= max_rounds <= 100):
        raise HTTPException(400, "Max rounds must be between 1 and 100")

    # Save uploaded files
    upload_dir = settings.upload_folder / "projects" / sim_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        if f.filename:
            dest = upload_dir / f.filename
            content = await f.read()
            async with aiofiles.open(dest, "wb") as fp:
                await fp.write(content)
            log.info("file_uploaded", sim_id=sim_id, file=f.filename, size=len(content))

    # Create simulation state
    sim = SimulationState(
        id=sim_id,
        status="initializing",
        current_phase="Queued",
        total_rounds=max_rounds,
        agent_count=agent_count,
        requirement=requirement,
    )
    set_simulation(sim)

    # Launch pipeline in background
    background_tasks.add_task(run_simulation_pipeline, sim_id)

    log.info("simulation_started", sim_id=sim_id, agents=agent_count, rounds=max_rounds)
    return SimulationStartResponse(simulation_id=sim_id)


# ── GET /{id}/status ─────────────────────────────────────────

@router.get("/{sim_id}/status", response_model=SimulationStatusResponse)
async def get_status(sim_id: str):
    """Get current simulation status."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(404, f"Simulation {sim_id} not found")

    return SimulationStatusResponse(
        id=sim.id,
        status=sim.status,
        current_phase=sim.current_phase,
        round=sim.round,
        total_rounds=sim.total_rounds,
        agent_count=sim.agent_count,
        graph_node_count=sim.graph_node_count,
        error=sim.error,
        created_at=sim.created_at,
        updated_at=sim.updated_at,
    )


# ── GET /{id}/agents ─────────────────────────────────────────

@router.get("/{sim_id}/agents", response_model=list[AgentResponse])
async def get_agents(sim_id: str):
    """Get all agents in a simulation."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(404, f"Simulation {sim_id} not found")

    return [
        AgentResponse(
            id=a.id,
            name=a.name,
            persona=a.persona,
            archetype=a.archetype,
            faction=a.faction,
            stance=a.stance,
            influence=a.influence,
            platform=a.platform,
            memory=a.memory,
        )
        for a in sim.agents
    ]


# ── GET /{id}/feed ───────────────────────────────────────────

@router.get("/{sim_id}/feed", response_model=list[PostResponse])
async def get_feed(sim_id: str, limit: int = 100, offset: int = 0):
    """Get the platform feed (most recent first)."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(404, f"Simulation {sim_id} not found")

    feed = list(reversed(sim.feed))  # newest first
    page = feed[offset : offset + limit]

    return [
        PostResponse(
            agent_id=f.agent_id,
            agent_name=f.agent_name,
            platform=f.platform,
            content=f.content,
            action_type=f.action_type,
            timestamp=f.timestamp,
            stance=f.stance,
            round_num=f.round_num,
        )
        for f in page
    ]


# ── GET /{id}/graph ──────────────────────────────────────────

@router.get("/{sim_id}/graph", response_model=GraphResponse)
async def get_graph(sim_id: str):
    """Get the knowledge graph."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(404, f"Simulation {sim_id} not found")

    return GraphResponse(nodes=sim.graph.nodes, edges=sim.graph.edges)


# ── GET /{id}/report ─────────────────────────────────────────

@router.get("/{sim_id}/report", response_model=ReportResponse)
async def get_report(sim_id: str):
    """Get the prediction report."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(404, f"Simulation {sim_id} not found")
    if not sim.report:
        raise HTTPException(404, "Report not yet generated")

    return ReportResponse(
        title=sim.report.title,
        executive_summary=sim.report.executive_summary,
        methodology=sim.report.methodology,
        confidence=sim.report.confidence,
        key_findings=sim.report.key_findings,
        factions=sim.report.factions,
    )


# ── POST /{id}/inject ────────────────────────────────────────

@router.post("/{sim_id}/inject")
async def inject_variable(sim_id: str, request: InjectVariableRequest):
    """God Mode: inject a variable into the running simulation."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(404, f"Simulation {sim_id} not found")

    feed_item = FeedItem(
        agent_id="system",
        agent_name="GOD MODE",
        platform="twitter",
        content=f"[INJECTED VARIABLE] {request.content}",
        action_type="inject",
        timestamp=time.time(),
        stance="neutral",
        round_num=sim.round,
    )
    sim.feed.append(feed_item)
    set_simulation(sim)

    bus = get_event_bus()
    await bus.publish(sim_id, "agent:action", feed_item.model_dump())

    return {"status": "injected"}


# ── GET /simulations (list) ──────────────────────────────────

list_router = APIRouter(tags=["simulation"])


@list_router.get("/api/simulations", response_model=list[SimulationSummaryResponse])
async def list_all_simulations():
    """List all simulations."""
    return [SimulationSummaryResponse(**s) for s in list_simulations()]

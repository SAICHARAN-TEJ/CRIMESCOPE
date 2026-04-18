# SPDX-License-Identifier: AGPL-3.0-only
"""Simulation router — start, stream, and query simulations."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.db.memory_store import store
from backend.db.supabase_client import get_supabase
from backend.demo.harlow_case import HARLOW_SEED
from backend.simulation.engine import SimulationEngine
from backend.utils.logger import get_logger

router = APIRouter()
logger = get_logger("crimescope.simulation.router")


@router.post("/simulate/{case_id}")
async def start_simulation(case_id: str):
    """Create a simulation record and return its ID."""
    client = get_supabase()
    sim_id = "demo"
    if client:
        try:
            res = client.table("simulations").insert(
                {"case_id": case_id, "status": "running"}
            ).execute()
            sim_id = res.data[0]["id"] if res.data else "demo"
        except Exception:
            pass

    if sim_id == "demo":
        sim = store.create_simulation(case_id)
        sim_id = sim["id"]

    return {"simulation_id": sim_id, "status": "started"}


@router.get("/simulate/{case_id}/stream")
async def stream_simulation(case_id: str):
    """SSE stream of the 30-round simulation."""
    seed = None

    # Try Supabase first
    client = get_supabase()
    if client:
        try:
            case_res = client.table("cases").select("seed_packet").eq("id", case_id).execute()
            if case_res.data:
                seed = case_res.data[0]["seed_packet"]
        except Exception:
            pass

    # Try in-memory store
    if not seed:
        seed = store.get_seed_packet(case_id)

    # Fallback to demo
    if not seed:
        if case_id == "harlow-001":
            seed = HARLOW_SEED
        else:
            logger.warning(f"No seed packet found for case {case_id} — using demo")
            seed = HARLOW_SEED

    logger.info(f"Starting simulation for case {case_id} — seed title: {seed.get('title', '?')}")
    engine = SimulationEngine(case_id, seed)
    return StreamingResponse(engine.stream(), media_type="text/event-stream")


@router.get("/simulate/{simulation_id}/status")
async def get_simulation_status(simulation_id: str):
    client = get_supabase()
    if client:
        try:
            res = client.table("simulations").select("*").eq("id", simulation_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    # Try memory store
    sim = store.get_simulation(simulation_id)
    if sim:
        return sim

    return {"id": simulation_id, "status": "demo", "rounds_completed": 0}

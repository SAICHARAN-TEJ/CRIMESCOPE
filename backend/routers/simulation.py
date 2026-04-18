# SPDX-License-Identifier: AGPL-3.0-only
"""Simulation router — start, stream, and query simulations."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.db.supabase_client import get_supabase
from backend.demo.harlow_case import HARLOW_SEED
from backend.simulation.engine import SimulationEngine

router = APIRouter()


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
    return {"simulation_id": sim_id, "status": "started"}


@router.get("/simulate/{case_id}/stream")
async def stream_simulation(case_id: str):
    """SSE stream of the 30-round simulation."""
    seed = HARLOW_SEED  # Default to demo

    client = get_supabase()
    if client:
        try:
            case_res = client.table("cases").select("seed_packet").eq("id", case_id).execute()
            if case_res.data:
                seed = case_res.data[0]["seed_packet"]
        except Exception:
            pass

    engine = SimulationEngine(case_id, seed)
    return StreamingResponse(engine.stream(), media_type="text/event-stream")


@router.get("/simulate/{simulation_id}/status")
async def get_simulation_status(simulation_id: str):
    client = get_supabase()
    if not client:
        return {"id": simulation_id, "status": "demo", "rounds_completed": 0}
    res = client.table("simulations").select("*").eq("id", simulation_id).execute()
    if not res.data:
        raise HTTPException(404, "Simulation not found")
    return res.data[0]

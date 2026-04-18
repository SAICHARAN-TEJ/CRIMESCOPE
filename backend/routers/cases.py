# SPDX-License-Identifier: AGPL-3.0-only
"""Cases router — CRUD for investigation cases."""

from fastapi import APIRouter, HTTPException

from backend.db.memory_store import store
from backend.db.models import CaseCreate
from backend.db.supabase_client import get_supabase
from backend.utils.logger import get_logger

router = APIRouter()
logger = get_logger("crimescope.cases")


@router.post("/cases")
async def create_case(body: CaseCreate):
    client = get_supabase()
    if client:
        try:
            res = client.table("cases").insert(body.model_dump()).execute()
            return res.data[0] if res.data else body.model_dump()
        except Exception:
            pass

    # In-memory fallback
    case = store.create_case(
        title=body.title,
        mode=body.mode,
        seed_packet=body.seed_packet if hasattr(body, "seed_packet") else {},
    )
    return case


@router.get("/cases")
async def list_cases():
    cases = []

    # Supabase cases
    client = get_supabase()
    if client:
        try:
            res = client.table("cases").select("*").order("created_at", desc=True).execute()
            cases.extend(res.data or [])
        except Exception:
            pass

    # In-memory cases
    mem_cases = store.list_cases()
    if mem_cases:
        cases.extend(mem_cases)

    # Always include demo case
    demo_ids = {c.get("id") for c in cases}
    if "harlow-001" not in demo_ids:
        cases.append({
            "id": "harlow-001",
            "title": "Harlow Street Investigation",
            "mode": 3,
            "status": "ready",
            "created_at": "2026-01-01T00:00:00Z",
        })

    return cases


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    # Try in-memory store
    case = store.get_case(case_id)
    if case:
        return case

    # Try Supabase
    client = get_supabase()
    if client:
        try:
            res = client.table("cases").select("*").eq("id", case_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    # Demo fallback
    if case_id == "harlow-001":
        return {"id": "harlow-001", "title": "Harlow Street Investigation", "mode": 3, "status": "ready"}

    raise HTTPException(404, "Case not found")

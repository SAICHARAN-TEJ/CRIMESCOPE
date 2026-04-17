"""Cases router — CRUD for investigation cases."""

from fastapi import APIRouter, HTTPException

from backend.db.models import CaseCreate
from backend.db.supabase_client import get_supabase

router = APIRouter()


@router.post("/cases")
async def create_case(body: CaseCreate):
    client = get_supabase()
    if not client:
        raise HTTPException(503, "Database unavailable — running in demo mode")
    res = client.table("cases").insert(body.model_dump()).execute()
    return res.data[0] if res.data else body.model_dump()


@router.get("/cases")
async def list_cases():
    client = get_supabase()
    if not client:
        # Return demo case list
        return [
            {
                "id": "harlow-001",
                "title": "Harlow Street Investigation",
                "mode": 3,
                "status": "ready",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ]
    res = client.table("cases").select("*").order("created_at", desc=True).execute()
    return res.data


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    client = get_supabase()
    if not client:
        if case_id == "harlow-001":
            return {"id": "harlow-001", "title": "Harlow Street Investigation", "mode": 3, "status": "ready"}
        raise HTTPException(404, "Case not found")
    res = client.table("cases").select("*").eq("id", case_id).execute()
    if not res.data:
        raise HTTPException(404, "Case not found")
    return res.data[0]

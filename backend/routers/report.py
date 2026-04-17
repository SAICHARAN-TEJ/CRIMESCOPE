"""Report router — final Probable Cause reports."""

from fastapi import APIRouter, HTTPException

from backend.db.supabase_client import get_supabase
from backend.demo.harlow_case import HARLOW_SEED

router = APIRouter()


@router.get("/report/{case_id}")
async def get_report(case_id: str):
    client = get_supabase()

    if client:
        try:
            res = client.table("reports").select("*").eq("case_id", case_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    # Demo fallback — generate a static report
    if case_id == "harlow-001":
        return {
            "case_id": "harlow-001",
            "report_json": {
                "case_id": "harlow-001",
                "title": "PROBABLE CAUSE REPORT",
                "consensus": 87,
                "hypotheses": [
                    {"id": "H-001", "title": "Planned Ambush", "probability": 0.45, "agent_count": 450},
                    {"id": "H-002", "title": "Staged Disappearance", "probability": 0.30, "agent_count": 300},
                    {"id": "H-003", "title": "Third-Party Opportunist", "probability": 0.15, "agent_count": 150},
                    {"id": "H-004", "title": "Accidental Discovery", "probability": 0.10, "agent_count": 100},
                ],
                "consensus_facts": [
                    "Vehicle entered garage at 06:42 PM.",
                    "Handbag intentionally placed in bin on Level 1.",
                    "22-minute CCTV blind spot from 06:58 to 07:20.",
                ],
                "dissent": "100 agents maintain alternative theory.",
            },
        }

    raise HTTPException(404, "Report not found. Run a simulation first.")

# SPDX-License-Identifier: AGPL-3.0-only
"""Report router — final Probable Cause reports with full schema."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.db.supabase_client import get_supabase
from backend.demo.harlow_case import HARLOW_SEED

router = APIRouter()


# ── Demo report (pre-computed ProbableCauseReport schema) ────────────────

DEMO_REPORT = {
    "case_id": "harlow-001",
    "title": "PROBABLE CAUSE REPORT",
    "consensus": 87,
    "hypotheses": [
        {
            "id": "H-001",
            "title": "Planned Ambush",
            "probability": 0.45,
            "agent_count": 450,
            "causal_chain": [
                {"step": 1, "event": "Perpetrator surveys garage CCTV schedule — identifies 22-min blind window", "certainty": 0.72},
                {"step": 2, "event": "Victim arrives at garage at 06:42 PM as per daily routine", "certainty": 0.95},
                {"step": 3, "event": "Perpetrator disables CCTV at 06:58 PM from utility room access", "certainty": 0.68},
                {"step": 4, "event": "Confrontation on Level 2 at 07:12 PM — 2 voices heard by Witness C", "certainty": 0.85},
                {"step": 5, "event": "Handbag staged in L1 bin to misdirect search — wallet intact, keys taken", "certainty": 0.78},
                {"step": 6, "event": "Red SUV exits at 07:15 PM via south ramp — Witness A confirms", "certainty": 0.70},
            ],
            "supporting_evidence": [
                "22-minute CCTV blackout correlates with utility room access log",
                "Witness C heard argument on L2 at 07:12 PM",
                "Boot prints (size 11) traced from L3 to utility staircase",
                "Dark jacket on stairwell railing — not victim's wardrobe",
            ],
            "contradicting_evidence": [
                "Arthur's gas receipt at 06:44 PM — 8km away",
            ],
        },
        {
            "id": "H-002",
            "title": "Staged Disappearance",
            "probability": 0.30,
            "agent_count": 300,
            "causal_chain": [
                {"step": 1, "event": "Victim orchestrates own disappearance to escape domestic situation", "certainty": 0.55},
                {"step": 2, "event": "Handbag planted to simulate crime scene", "certainty": 0.60},
                {"step": 3, "event": "Pre-arranged vehicle collects victim during CCTV gap", "certainty": 0.50},
            ],
            "supporting_evidence": [
                "$500k insurance policy filed 6 months prior",
                "Handbag placement appears deliberate — wallet intact",
            ],
            "contradicting_evidence": [
                "Blood trace on L3 pillar contradicts voluntary departure",
                "Witness C heard argument — not consistent with staged exit",
            ],
        },
        {
            "id": "H-003",
            "title": "Third-Party Opportunist",
            "probability": 0.15,
            "agent_count": 150,
            "causal_chain": [
                {"step": 1, "event": "Unrelated criminal exploits CCTV failure for separate crime", "certainty": 0.40},
                {"step": 2, "event": "Victim becomes collateral during garage encounter", "certainty": 0.35},
            ],
            "supporting_evidence": [
                "Red SUV not linked to any known associates",
                "Boot print size 11 doesn't match Arthur or known contacts",
            ],
            "contradicting_evidence": [
                "Deliberate handbag staging suggests premeditation, not opportunity",
            ],
        },
        {
            "id": "H-004",
            "title": "Accidental Discovery",
            "probability": 0.07,
            "agent_count": 70,
            "causal_chain": [
                {"step": 1, "event": "Victim discovers illicit activity in garage", "certainty": 0.30},
                {"step": 2, "event": "Perpetrators eliminate witness", "certainty": 0.25},
            ],
            "supporting_evidence": [],
            "contradicting_evidence": [
                "No evidence of illicit activity in garage",
            ],
        },
        {
            "id": "H-005",
            "title": "Insurance Fraud Scheme",
            "probability": 0.03,
            "agent_count": 30,
            "causal_chain": [
                {"step": 1, "event": "Arthur and accomplice stage disappearance for $500k payout", "certainty": 0.20},
            ],
            "supporting_evidence": [
                "$500k insurance policy — Arthur sole beneficiary",
            ],
            "contradicting_evidence": [
                "Blood evidence on L3 pillar argues against staged event",
                "Gas receipt alibi would be unnecessary in cooperative scheme",
            ],
        },
    ],
    "consensus_facts": [
        "Victim left pharmacy at 06:38 PM, arrived at garage within 4 minutes",
        "CCTV system experienced a 22-minute failure from 06:58 to 07:20 PM",
        "Handbag deliberately concealed in L1 trash bin — wallet intact, keys missing",
        "Witness C reported argument on L2 at 07:12 PM — 2 voices heard",
        "Blood trace on L3 pillar — DNA analysis pending confirmation",
        "Unidentified red SUV observed departing at 07:15 PM by Witness A",
        "Size 11 boot prints traced from L3 to utility staircase",
        "Dark jacket found on stairwell railing — not victim's wardrobe",
        "$500k insurance policy filed 6 months prior — Arthur sole beneficiary",
        "Gas receipt places Arthur 8km away at 06:44 PM — timeline disputed",
    ],
    "dissent": [
        {"agent": "behavioral_profiler_0003", "hypothesis": "Staged Disappearance", "summary": "Insurance motive is insufficient without additional financial distress evidence"},
        {"agent": "contradiction_detector_0022", "hypothesis": "Planned Ambush", "summary": "Red SUV sighting conflicts with tire marks in alley — pattern suggests different vehicle class"},
        {"agent": "alibi_verifier_0014", "hypothesis": "Planned Ambush", "summary": "Arthur's gas receipt creates 14-minute gap — physically possible but statistically unlikely"},
    ],
    "agent_count": 1000,
    "rounds_completed": 30,
    "convergence_score": 0.87,
}


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

    # Demo fallback — return the full pre-computed report
    if case_id == "harlow-001":
        return DEMO_REPORT

    raise HTTPException(404, "Report not found. Run a simulation first.")


@router.get("/report/{case_id}/json")
async def get_report_json(case_id: str):
    """Download the raw report as JSON (for export)."""
    report = await get_report(case_id)
    return JSONResponse(content=report, media_type="application/json")

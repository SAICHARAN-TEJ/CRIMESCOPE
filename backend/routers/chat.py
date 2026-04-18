# SPDX-License-Identifier: AGPL-3.0-only
"""Chat router — post-simulation Q&A with the swarm and individual agents."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.memory_store import store
from backend.demo.harlow_case import HARLOW_SEED
from backend.utils.openrouter import openrouter
from backend.config import settings
from backend.utils.logger import get_logger

router = APIRouter()
logger = get_logger("crimescope.chat")


class ChatRequest(BaseModel):
    question: str


def _get_case_context(case_id: str) -> str:
    """Load case context from memory store, Supabase, or demo fallback."""
    # Try in-memory store first
    seed = store.get_seed_packet(case_id)
    if seed:
        return str(seed)

    # Try Supabase
    from backend.db.supabase_client import get_supabase
    client = get_supabase()
    if client:
        try:
            res = client.table("cases").select("seed_packet").eq("id", case_id).execute()
            if res.data:
                return str(res.data[0]["seed_packet"])
        except Exception:
            pass

    # Demo fallback
    if case_id == "harlow-001":
        return str(HARLOW_SEED)

    return "No case data available. Please upload evidence first."


# ── Case-level chat ──────────────────────────────────────────────────────

@router.post("/chat/{case_id}")
async def chat(case_id: str, body: ChatRequest):
    """
    Simple RAG-lite chat — feeds the question + case context
    through the reasoning model for a grounded answer.
    """
    context = _get_case_context(case_id)

    answer = await openrouter.chat(
        settings.reasoning_model_name,
        f"CASE CONTEXT:\n{context[:3000]}\n\nQUESTION: {body.question}",
        system=(
            "You are the CrimeScope swarm intelligence analyst. "
            "Answer based strictly on the case evidence provided."
        ),
    )
    return {"case_id": case_id, "question": body.question, "answer": answer}


# ── Report-level chat (ReportAgent) ──────────────────────────────────────

@router.post("/report-chat/{case_id}")
async def report_chat(case_id: str, body: ChatRequest):
    """
    ReportAgent chat — answers questions about the final Probable Cause
    Report with full context of hypotheses and dissent.
    """
    from backend.routers.report import get_report
    try:
        report = await get_report(case_id)
    except Exception:
        report = {"error": "Report not generated yet"}

    answer = await openrouter.chat(
        settings.reasoning_model_name,
        f"REPORT:\n{str(report)[:4000]}\n\nQUESTION: {body.question}",
        system=(
            "You are the CrimeScope ReportAgent. You have full access to the "
            "Probable Cause Report. Answer questions about hypotheses, evidence, "
            "agent consensus, and dissent. Be precise and cite specific findings."
        ),
    )
    return {"case_id": case_id, "question": body.question, "answer": answer, "type": "report_agent"}


# ── Agent interrogation ─────────────────────────────────────────────────

@router.get("/agent/{agent_id}/chat")
async def get_agent_profile(agent_id: str):
    """
    Return the agent's archetype and persona for interrogation UI.
    In production, this would query the swarm manager.
    """
    # Parse archetype from agent_id (e.g., "forensic_analyst_0042")
    parts = agent_id.rsplit("_", 1)
    archetype = parts[0].replace("_", " ").title() if parts else "Unknown"
    return {
        "agent_id": agent_id,
        "archetype": archetype,
        "status": "available",
    }


@router.post("/agent/{agent_id}/chat")
async def interrogate_agent(agent_id: str, body: ChatRequest):
    """
    Ask a specific agent about their reasoning, vote, and causal chain.
    """
    parts = agent_id.rsplit("_", 1)
    archetype = parts[0].replace("_", " ").title() if parts else "Unknown"

    answer = await openrouter.chat(
        settings.fast_model_name,
        f"QUESTION: {body.question}",
        system=(
            f"You are Agent {agent_id}, a {archetype} in the CrimeScope swarm. "
            f"You participated in a 30-round criminal investigation simulation. "
            f"Answer the interrogator's question from your perspective as a {archetype}. "
            f"Explain your reasoning, what evidence influenced your vote, and any "
            f"contradictions you detected."
        ),
    )
    return {
        "agent_id": agent_id,
        "archetype": archetype,
        "question": body.question,
        "answer": answer,
        "type": "agent_interrogation",
    }

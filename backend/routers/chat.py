# SPDX-License-Identifier: AGPL-3.0-only
"""Chat router — GraphRAG-powered Q&A with connected evidence paths."""

import hashlib

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
    GraphRAG-powered chat — retrieves connected evidence paths from the
    knowledge graph, plus ChromaDB vector memories, then synthesises
    an answer via the reasoning model.
    """
    # ── Check Redis cache ────────────────────────────────────────────
    cache_key = f"chat:{case_id}:{hashlib.md5(body.question.encode()).hexdigest()}"
    try:
        from backend.infrastructure.redis_client import redis_cache
        cached = await redis_cache.get_json(cache_key)
        if cached:
            logger.info(f"Chat cache hit: {cache_key}")
            return cached
    except Exception:
        pass

    context = _get_case_context(case_id)

    # ── GraphRAG retrieval — connected evidence paths ────────────────
    graph_context = ""
    try:
        from backend.graph.neo4j_client import neo4j_client
        from backend.graph.traversal import GraphTraversal
        traversal = GraphTraversal(neo4j_client)
        paths = await traversal.graph_rag_retrieve(case_id, body.question, max_hops=3, top_k=5)
        if paths:
            path_summaries = [f"• {p.summarize()} (certainty: {p.cumulative_certainty:.0%})" for p in paths]
            graph_context = "\n\nCONNECTED EVIDENCE PATHS (from Knowledge Graph):\n" + "\n".join(path_summaries)
            logger.info(f"GraphRAG: {len(paths)} evidence paths retrieved")
    except Exception as e:
        logger.warning(f"GraphRAG traversal failed: {e}")

    # ── ChromaDB vector retrieval (complementary) ────────────────────
    rag_fragments = []
    try:
        from backend.simulation.engine import SimulationEngine
        results = SimulationEngine.query_rag(case_id, body.question, top_k=8)
        rag_fragments = [r.get("text", "") for r in results if r.get("text")]
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")

    rag_context = ""
    if rag_fragments:
        rag_context = "\n\nRELEVANT MEMORIES (from Vector Store):\n" + "\n".join(f"• {f}" for f in rag_fragments)

    answer = await openrouter.chat(
        settings.reasoning_model_name,
        f"CASE CONTEXT:\n{context[:3000]}{graph_context}{rag_context}\n\nQUESTION: {body.question}",
        system=(
            "You are the CrimeScope swarm intelligence analyst. "
            "Answer based strictly on the case evidence, connected evidence paths "
            "from the knowledge graph, and retrieved memories. "
            "Cite specific entities, timeline events, and relationships. "
            "When evidence paths show contradictions, highlight them explicitly."
        ),
    )

    result = {"case_id": case_id, "question": body.question, "answer": answer}

    # ── Cache result ─────────────────────────────────────────────────
    try:
        from backend.infrastructure.redis_client import redis_cache
        await redis_cache.set_json(cache_key, result, ttl=300)  # 5 min cache
    except Exception:
        pass

    return result


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

# SPDX-License-Identifier: AGPL-3.0-only
"""Graph router — knowledge-graph serialisation for the D3 frontend."""

from fastapi import APIRouter

from backend.db.memory_store import store
from backend.db.supabase_client import get_supabase
from backend.demo.harlow_case import HARLOW_NODES, HARLOW_EDGES

router = APIRouter()


@router.get("/graph/{case_id}")
async def get_graph(case_id: str, round: int | None = None):
    """
    Return graph data for the D3 visualiser.
    Priority:
      1. Demo (harlow-001): pre-built dataset
      2. round-specific snapshot from Supabase or memory store
      3. Live graph from unified graph client (Neo4j or in-memory)
    """
    if case_id == "harlow-001":
        return {"nodes": HARLOW_NODES, "edges": HARLOW_EDGES}

    # Round-specific snapshot
    if round is not None:
        # Try in-memory snapshots first
        snapshots = store._graph_snapshots.get(case_id, [])
        for snap in snapshots:
            if snap.get("round_number") == round:
                return snap

        # Try Supabase
        client = get_supabase()
        if client:
            try:
                res = (
                    client.table("graph_snapshots")
                    .select("*")
                    .eq("case_id", case_id)
                    .eq("round_number", round)
                    .execute()
                )
                if res.data:
                    return res.data[0]
            except Exception:
                pass

    # Live graph from the unified graph client (works without Neo4j)
    try:
        from backend.graph.neo4j_client import neo4j_client
        return await neo4j_client.get_graph(case_id)
    except Exception:
        return {"nodes": [], "edges": []}

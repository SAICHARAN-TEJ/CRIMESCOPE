# SPDX-License-Identifier: AGPL-3.0-only
"""Graph router — knowledge-graph serialisation for the D3 frontend."""

from fastapi import APIRouter

from backend.db.supabase_client import get_supabase
from backend.demo.harlow_case import HARLOW_NODES, HARLOW_EDGES

router = APIRouter()


@router.get("/graph/{case_id}")
async def get_graph(case_id: str, round: int | None = None):
    """
    Return graph data for the D3 visualiser.
    If round is specified, fetch the snapshot from Supabase.
    If 'demo', return the pre-built Harlow dataset.
    Otherwise, query Neo4j live.
    """
    if case_id == "harlow-001":
        return {"nodes": HARLOW_NODES, "edges": HARLOW_EDGES}

    if round is not None:
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

    try:
        from backend.graph.neo4j_client import neo4j_client
        return await neo4j_client.get_graph(case_id)
    except Exception:
        return {"nodes": [], "edges": []}

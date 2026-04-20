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
      4. Seed-derived graph from raw entities
    """
    if case_id == "harlow-001":
        return {"nodes": HARLOW_NODES, "edges": HARLOW_EDGES, "title": "Harlow Street Incident"}

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
        graph = await neo4j_client.get_graph(case_id)
        if graph.get("nodes"):
            seed = store.get_seed_packet(case_id)
            graph["title"] = seed.get("title", f"Case {case_id[:8]}") if seed else f"Case {case_id[:8]}"
            return graph
    except Exception:
        pass

    # Fallback: build graph from the seed packet directly
    seed = store.get_seed_packet(case_id)
    if seed:
        nodes = []
        edges = []
        node_ids = set()

        # Build nodes from entities
        for e in seed.get("entities", []):
            if isinstance(e, dict):
                nid = e.get("name", "").replace(" ", "_")
                if nid and nid not in node_ids:
                    nodes.append({
                        "id": nid, "label": e.get("name", "?"),
                        "type": (e.get("type", "evidence")).lower(),
                        "certainty": e.get("confidence", 0.8),
                    })
                    node_ids.add(nid)

        # Build nodes from key persons
        for p in seed.get("key_persons", []):
            if isinstance(p, dict):
                nid = p.get("name", "").replace(" ", "_")
                if nid and nid not in node_ids:
                    nodes.append({
                        "id": nid, "label": p.get("name", "?"),
                        "type": "person",
                        "certainty": 0.9,
                    })
                    node_ids.add(nid)

        # Auto-connect persons to entities with plausible relationships
        person_ids = [n["id"] for n in nodes if n["type"] == "person"]
        evidence_ids = [n["id"] for n in nodes if n["type"] != "person"]
        for pi in person_ids:
            for ei in evidence_ids[:3]:  # connect each person to first 3 non-person nodes
                edges.append({
                    "source": pi, "target": ei,
                    "type": "related_to", "label": "related_to",
                    "certainty": 0.7,
                })

        return {"nodes": nodes, "edges": edges, "title": seed.get("title", f"Case {case_id[:8]}")}

    return {"nodes": [], "edges": [], "title": f"Case {case_id[:8]}"}


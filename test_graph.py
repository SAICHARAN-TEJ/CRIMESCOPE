"""Quick smoke test for the in-memory graph store."""
import asyncio
from backend.graph.neo4j_client import neo4j_client


async def test():
    await neo4j_client.connect()

    # Build graph from seed
    seed = {
        "victim": "Jane Doe",
        "location": "Central Park",
        "key_persons": [
            {"name": "John Smith", "role": "suspect", "credibility": 0.7},
            {"name": "Alice Brown", "role": "witness", "credibility": 0.9},
        ],
        "entities": [
            {"name": "Knife", "type": "Evidence", "description": "Found at scene", "confidence": 0.85},
        ],
    }
    await neo4j_client.build_from_seed("test-001", seed)

    graph = await neo4j_client.get_graph("test-001")
    print(f"Nodes: {len(graph['nodes'])}")
    for n in graph["nodes"]:
        print(f"  - {n['label']} ({n['type']})")

    summary = await neo4j_client.get_summary("test-001")
    print(f"Summary: {summary}")

    # Add findings
    await neo4j_client.add_agent_findings("test-001", 1, [
        {"type": "relationship", "source": "John Smith", "target": "Knife", "label": "POSSESSED"},
    ])

    graph2 = await neo4j_client.get_graph("test-001")
    print(f"After findings - Nodes: {len(graph2['nodes'])}, Edges: {len(graph2['edges'])}")
    for e in graph2["edges"]:
        print(f"  - {e['source']} --[{e['type']}]--> {e['target']}")

    # Cleanup
    await neo4j_client.cleanup("test-001")
    graph3 = await neo4j_client.get_graph("test-001")
    print(f"After cleanup - Nodes: {len(graph3['nodes'])}, Edges: {len(graph3['edges'])}")

    print("\n✓ All in-memory graph tests passed!")


if __name__ == "__main__":
    asyncio.run(test())

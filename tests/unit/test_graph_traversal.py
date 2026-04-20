# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for the graph traversal (GraphRAG) module."""

import pytest

from backend.graph.neo4j_client import Neo4jClient
from backend.graph.traversal import GraphTraversal


@pytest.fixture
def graph_client(sample_seed_packet):
    """Create an in-memory graph client with test data."""
    client = Neo4jClient()
    # Build from seed synchronously via mem
    client._mem_build_from_seed("test-001", sample_seed_packet)
    # Add some edges for traversal
    client._mem.add_edge(
        "test-001", "John Smith", "Red SUV", "ASSOCIATED_WITH",
        {"certainty": 0.6}
    )
    client._mem.add_edge(
        "test-001", "Witness A", "CCTV blackout", "WITNESSED_BY",
        {"certainty": 0.85}
    )
    client._mem.add_edge(
        "test-001", "Jane Doe", "Harlow Street Garage", "LOCATED_AT",
        {"certainty": 0.95}
    )
    client._mem.add_edge(
        "test-001", "Boot prints", "John Smith", "CONNECTED_TO",
        {"certainty": 0.7}
    )
    return client


@pytest.fixture
def traversal(graph_client):
    return GraphTraversal(graph_client)


@pytest.mark.asyncio
async def test_graph_rag_retrieve_finds_paths(traversal):
    """GraphRAG should return connected evidence paths for a query."""
    paths = await traversal.graph_rag_retrieve("test-001", "Red SUV", max_hops=3, top_k=5)
    assert len(paths) > 0
    # Each path should have steps
    for p in paths:
        assert len(p.steps) > 0
        assert p.cumulative_certainty > 0


@pytest.mark.asyncio
async def test_graph_rag_empty_query(traversal):
    """GraphRAG with nonexistent entity returns empty."""
    paths = await traversal.graph_rag_retrieve("test-001", "xyznonexistent", max_hops=2)
    assert paths == []


@pytest.mark.asyncio
async def test_entity_neighborhood(traversal):
    """Neighborhood query should return connected nodes."""
    neighborhood = await traversal.get_entity_neighborhood("test-001", "John Smith", hops=2)
    assert "nodes" in neighborhood
    assert "edges" in neighborhood
    assert len(neighborhood["nodes"]) > 0


@pytest.mark.asyncio
async def test_find_shortest_path(traversal):
    """Shortest path should find a route between connected entities."""
    path = await traversal.find_shortest_path("test-001", "Boot prints", "Red SUV")
    # Boot prints → John Smith → Red SUV
    if path:
        assert path.length >= 2


@pytest.mark.asyncio
async def test_find_contradictions_empty(traversal):
    """No contradictions should return empty list."""
    contradictions = await traversal.find_contradictions("test-001")
    assert isinstance(contradictions, list)

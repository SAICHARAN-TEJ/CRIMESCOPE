# SPDX-License-Identifier: AGPL-3.0-only
"""
GraphRAG Traversal — graph-walk retrieval that replaces pure vector similarity.

Core algorithm:
  1. Vector-search ChromaDB to find seed entities matching the query
  2. For each seed entity, traverse the knowledge graph N hops outward
  3. Collect all connected nodes and their relationships as "evidence paths"
  4. Rank paths by cumulative certainty × relevance score
  5. Return top-K paths with full context

This is the key differentiator: instead of returning isolated text chunks,
we return CONNECTED EVIDENCE PATHS through the knowledge graph.
"""

from __future__ import annotations

import hashlib
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.graph.schema import EvidencePath, EvidencePathStep
from backend.utils.logger import get_logger

logger = get_logger("crimescope.graph.traversal")


class GraphTraversal:
    """Traverses the in-memory or Neo4j graph to find evidence paths."""

    def __init__(self, graph_client) -> None:
        """
        Args:
            graph_client: The unified Neo4jClient (uses its _mem InMemoryGraph
                          or Neo4j driver depending on connection state).
        """
        self._client = graph_client

    async def graph_rag_retrieve(
        self,
        case_id: str,
        query: str,
        max_hops: int = 3,
        top_k: int = 5,
    ) -> List[EvidencePath]:
        """
        Full GraphRAG retrieval pipeline:
          1. Find seed entities via vector search
          2. Expand each seed through graph traversal
          3. Rank and return top-K evidence paths
        """
        # Step 1: Vector search for seed entities
        seed_entities = await self._find_seed_entities(case_id, query)

        if not seed_entities:
            logger.debug(f"No seed entities found for query: {query[:80]}")
            return []

        # Step 2: Traverse graph from each seed
        all_paths: List[EvidencePath] = []
        for seed_name in seed_entities[:5]:  # Limit seeds to avoid explosion
            paths = await self._traverse_from_entity(case_id, seed_name, max_hops)
            all_paths.extend(paths)

        # Step 3: Rank by cumulative certainty, deduplicate
        all_paths.sort(key=lambda p: p.cumulative_certainty, reverse=True)
        seen: Set[str] = set()
        unique_paths: List[EvidencePath] = []
        for p in all_paths:
            key = p.summarize()
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)

        result = unique_paths[:top_k]
        logger.info(
            f"GraphRAG: query='{query[:50]}' → {len(seed_entities)} seeds → "
            f"{len(all_paths)} paths → {len(result)} unique (top-{top_k})"
        )
        return result

    async def find_shortest_path(
        self, case_id: str, entity_a: str, entity_b: str
    ) -> Optional[EvidencePath]:
        """BFS shortest path between two named entities."""
        graph = await self._client.get_graph(case_id)
        nodes = {n.get("label", n.get("id", "")): n for n in graph.get("nodes", [])}
        edges = graph.get("edges", [])

        if entity_a not in nodes or entity_b not in nodes:
            return None

        # Build adjacency from edges
        adjacency: Dict[str, List[Tuple[str, Dict]]] = {}
        for e in edges:
            src = e.get("source", "")
            tgt = e.get("target", "")
            # Map edge source/target to node labels
            src_label = self._resolve_label(src, nodes)
            tgt_label = self._resolve_label(tgt, nodes)
            adjacency.setdefault(src_label, []).append((tgt_label, e))
            adjacency.setdefault(tgt_label, []).append((src_label, e))

        # BFS
        queue = deque([(entity_a, [entity_a], [])])
        visited: Set[str] = {entity_a}

        while queue:
            current, path, edge_path = queue.popleft()
            if current == entity_b:
                return self._build_path(path, edge_path, nodes)
            for neighbor, edge in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor], edge_path + [edge]))

        return None

    async def find_contradictions(self, case_id: str) -> List[Dict[str, Any]]:
        """Return all CONTRADICTS edges with connected node context."""
        graph = await self._client.get_graph(case_id)
        nodes_by_id = {}
        for n in graph.get("nodes", []):
            nodes_by_id[n.get("id", "")] = n
            nodes_by_id[n.get("label", "")] = n

        contradictions = []
        for e in graph.get("edges", []):
            edge_type = e.get("type", "").upper()
            if "CONTRADICT" in edge_type:
                src = nodes_by_id.get(e.get("source", ""), {})
                tgt = nodes_by_id.get(e.get("target", ""), {})
                contradictions.append({
                    "source": src.get("label", e.get("source", "?")),
                    "target": tgt.get("label", e.get("target", "?")),
                    "edge": e,
                    "source_node": src,
                    "target_node": tgt,
                })

        return contradictions

    async def get_entity_neighborhood(
        self, case_id: str, entity_name: str, hops: int = 2
    ) -> Dict[str, Any]:
        """Return the local subgraph around an entity."""
        graph = await self._client.get_graph(case_id)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # Find the target node
        target_ids: Set[str] = set()
        for n in nodes:
            if n.get("label", "").lower() == entity_name.lower() or \
               n.get("id", "").lower() == entity_name.lower():
                target_ids.add(n.get("id", ""))
                target_ids.add(n.get("label", ""))

        if not target_ids:
            return {"nodes": [], "edges": []}

        # BFS expansion
        visited: Set[str] = set(target_ids)
        frontier: Set[str] = set(target_ids)

        for _ in range(hops):
            next_frontier: Set[str] = set()
            for e in edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                if src in frontier and tgt not in visited:
                    visited.add(tgt)
                    next_frontier.add(tgt)
                elif tgt in frontier and src not in visited:
                    visited.add(src)
                    next_frontier.add(src)
            frontier = next_frontier
            if not frontier:
                break

        # Filter nodes and edges to the neighborhood
        neighborhood_nodes = [
            n for n in nodes
            if n.get("id", "") in visited or n.get("label", "") in visited
        ]
        neighborhood_edges = [
            e for e in edges
            if (e.get("source", "") in visited or e.get("target", "") in visited)
        ]

        return {"nodes": neighborhood_nodes, "edges": neighborhood_edges}

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _find_seed_entities(self, case_id: str, query: str) -> List[str]:
        """Find entity names that match the query via vector search + keyword."""
        seed_names: List[str] = []

        # Vector search via ChromaDB
        try:
            from backend.memory.chroma_client import memory_client
            results = memory_client.search(f"rag:{case_id}", query, top_k=8)
            for r in results:
                meta = r.get("metadata", {})
                name = meta.get("name", "")
                if name:
                    seed_names.append(name)
        except Exception as e:
            logger.debug(f"ChromaDB seed search failed: {e}")

        # Keyword fallback: match query terms against node labels
        try:
            graph = await self._client.get_graph(case_id)
            query_lower = query.lower()
            for n in graph.get("nodes", []):
                label = n.get("label", "").lower()
                if label and any(term in label for term in query_lower.split()):
                    seed_names.append(n.get("label", ""))
        except Exception:
            pass

        # Deduplicate while preserving order
        seen: Set[str] = set()
        unique: List[str] = []
        for name in seed_names:
            if name.lower() not in seen:
                seen.add(name.lower())
                unique.append(name)

        return unique

    async def _traverse_from_entity(
        self, case_id: str, start_name: str, max_hops: int
    ) -> List[EvidencePath]:
        """BFS from a starting entity, collecting all paths up to max_hops."""
        graph = await self._client.get_graph(case_id)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # Build adjacency
        adjacency: Dict[str, List[Tuple[str, Dict, Dict]]] = {}
        node_map: Dict[str, Dict] = {}
        for n in nodes:
            key = n.get("label", n.get("id", ""))
            node_map[key] = n
            node_map[n.get("id", "")] = n

        for e in edges:
            src = self._resolve_label(e.get("source", ""), node_map)
            tgt = self._resolve_label(e.get("target", ""), node_map)
            src_node = node_map.get(src, {"label": src})
            tgt_node = node_map.get(tgt, {"label": tgt})
            adjacency.setdefault(src, []).append((tgt, e, tgt_node))
            adjacency.setdefault(tgt, []).append((src, e, src_node))

        # BFS collecting paths
        paths: List[EvidencePath] = []
        start_node = node_map.get(start_name, {"label": start_name, "type": "unknown"})
        queue: deque = deque([(start_name, [start_name], [], 0)])
        visited: Set[str] = {start_name}

        while queue:
            current, node_path, edge_path, hop = queue.popleft()
            if hop > 0:
                path = self._build_path(node_path, edge_path, node_map)
                if path:
                    paths.append(path)

            if hop < max_hops:
                for neighbor, edge, neighbor_node in adjacency.get(current, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((
                            neighbor,
                            node_path + [neighbor],
                            edge_path + [edge],
                            hop + 1,
                        ))

        return paths

    def _build_path(
        self,
        node_names: List[str],
        edges: List[Dict],
        node_map: Dict[str, Dict],
    ) -> Optional[EvidencePath]:
        """Build an EvidencePath from a list of node names and edges."""
        steps: List[EvidencePathStep] = []
        total_certainty = 0.0

        for i, name in enumerate(node_names):
            node = node_map.get(name, {"label": name, "type": "unknown"})
            edge = edges[i] if i < len(edges) else None
            node_cert = float(node.get("certainty", 0.5))
            total_certainty += node_cert

            steps.append(EvidencePathStep(
                node={
                    "name": node.get("label", name),
                    "type": node.get("type", "unknown"),
                    "certainty": node_cert,
                    "properties": node.get("properties", {}),
                },
                edge={
                    "type": edge.get("type", edge.get("label", "RELATED")),
                    "certainty": float(edge.get("certainty", 0.5)),
                } if edge else None,
                hop=i,
            ))

        if not steps:
            return None

        avg_certainty = total_certainty / len(steps) if steps else 0.0
        path = EvidencePath(
            steps=steps,
            cumulative_certainty=round(avg_certainty, 4),
        )
        path.path_description = path.summarize()
        return path

    @staticmethod
    def _resolve_label(id_or_label: str, node_map: Dict[str, Dict]) -> str:
        """Resolve a node ID to its label (name)."""
        node = node_map.get(id_or_label)
        if node:
            return node.get("label", id_or_label)
        return id_or_label

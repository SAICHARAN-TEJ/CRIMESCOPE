"""
CrimeScope — Graph Writer Agent.

Writes extracted entities and relationships to Neo4j using
idempotent MERGE operations. Also publishes GRAPH_NODE_ADD and
GRAPH_EDGE_ADD events for real-time frontend visualization.

All operations are batched for performance and safe for concurrent execution.
"""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.engine.agents.base import BaseAgent
from app.graph.driver import get_neo4j
from app.schemas.events import (
    AgentResult, AgentType, EventType, GraphEdgeEvent, GraphNodeEvent, WSEvent,
)

logger = get_logger("crimescope.agent.graph")

# Map entity types to Neo4j labels
_LABEL_MAP = {
    "person": "Person",
    "location": "Location",
    "event": "Event",
    "evidence": "Evidence",
    "vehicle": "Vehicle",
    "weapon": "Weapon",
    "organization": "Organization",
    "document": "Document",
}


class GraphAgent(BaseAgent):
    """
    Writes entities and relationships to Neo4j.
    All writes use MERGE — safe for duplicate/concurrent calls.
    Publishes graph events for real-time frontend updates.
    """

    agent_type = AgentType.GRAPH
    agent_name = "graph_agent"

    async def _execute(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        entities = payload.get("entities", [])
        relationships = payload.get("relationships", [])

        if not entities and not relationships:
            return AgentResult(
                agent=self.agent_type,
                success=True,
                facts=["No graph data to write"],
            )

        neo4j = get_neo4j()
        redis = get_redis()
        facts: list[str] = []

        # ── Write Nodes ──────────────────────────────────────────────
        nodes_written = 0
        for entity in entities:
            etype = entity.get("type", "Evidence").lower()
            label = _LABEL_MAP.get(etype, "Evidence")
            node_id = entity.get("id", entity.get("name", ""))
            name = entity.get("name", node_id)
            properties = entity.get("properties", {})
            properties["name"] = name
            properties["entity_type"] = etype

            try:
                await neo4j.merge_node(job_id, label, node_id, properties)
                nodes_written += 1

                # Publish real-time graph event
                await redis.publish_event(job_id, WSEvent(
                    event=EventType.GRAPH_NODE_ADD,
                    job_id=job_id,
                    agent=self.agent_type,
                    data=GraphNodeEvent(
                        id=node_id,
                        label=name,
                        type=etype,
                        properties=properties,
                    ).model_dump(),
                ).model_dump())
            except Exception as e:
                logger.warning(f"Node MERGE failed for {name}: {e}")

        facts.append(f"Wrote {nodes_written}/{len(entities)} nodes to Neo4j")

        # ── Write Relationships ──────────────────────────────────────
        edges_written = 0
        for rel in relationships:
            source_id = rel.get("source_id", rel.get("source", ""))
            target_id = rel.get("target_id", rel.get("target", ""))
            rel_type = rel.get("type", "RELATED_TO").upper().replace(" ", "_")
            properties = rel.get("properties", {})

            if not source_id or not target_id:
                continue

            # Determine labels (best effort — use Evidence as default)
            source_label = self._find_label(entities, source_id)
            target_label = self._find_label(entities, target_id)

            try:
                await neo4j.merge_relationship(
                    job_id, source_label, source_id,
                    target_label, target_id, rel_type, properties,
                )
                edges_written += 1

                await redis.publish_event(job_id, WSEvent(
                    event=EventType.GRAPH_EDGE_ADD,
                    job_id=job_id,
                    agent=self.agent_type,
                    data=GraphEdgeEvent(
                        source=source_id,
                        target=target_id,
                        label=rel_type,
                        properties=properties,
                    ).model_dump(),
                ).model_dump())
            except Exception as e:
                logger.warning(f"Relationship MERGE failed {source_id}→{target_id}: {e}")

        facts.append(f"Wrote {edges_written}/{len(relationships)} relationships to Neo4j")

        return AgentResult(
            agent=self.agent_type,
            success=True,
            entities=entities,
            relationships=relationships,
            facts=facts,
        )

    @staticmethod
    def _find_label(entities: list[dict], entity_id: str) -> str:
        """Find the Neo4j label for an entity by ID."""
        for ent in entities:
            eid = ent.get("id", ent.get("name", ""))
            if eid == entity_id:
                etype = ent.get("type", "evidence").lower()
                return _LABEL_MAP.get(etype, "Evidence")
        return "Evidence"

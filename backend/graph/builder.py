# SPDX-License-Identifier: AGPL-3.0-only
"""
GraphBuilder — LLM-assisted knowledge graph construction.

Extends the graph client with MERGE-based upserts, certainty properties,
and an LLM extraction step to convert natural language evidence into
structured graph triples.

Resilient: works without Neo4j by storing triples in the in-memory
graph inside neo4j_client.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.graph.neo4j_client import neo4j_client
from backend.llm import ModelRouter
from backend.utils.openrouter import openrouter
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("crimescope.graph.builder")


# ── GraphStorage abstraction (spec requirement) ─────────────────────────

class GraphStorage(ABC):
    """Abstract base for knowledge graph storage backends."""

    @abstractmethod
    def upsert_node(self, node_id: str, labels: List[str], props: Dict[str, Any]) -> None: ...

    @abstractmethod
    def upsert_edge(self, src: str, tgt: str, rel_type: str, props: Dict[str, Any]) -> None: ...

    @abstractmethod
    def get_graph_summary(self, case_id: str) -> Dict[str, Any]: ...

    @abstractmethod
    def cleanup(self, case_id: str) -> None: ...


class CrimeScopeGraphStorage(GraphStorage):
    """Graph storage that delegates to the unified neo4j_client.
    Works in both Neo4j-connected and in-memory-only modes."""

    def upsert_node(self, node_id: str, labels: List[str], props: Dict[str, Any]) -> None:
        case_id = props.get("case_id", "unknown")
        name = props.get("name", node_id)
        neo4j_client._mem.add_node(case_id, name, labels, {**props, "id": node_id})

        # If Neo4j is connected, also write there (sync via run_in_executor not
        # ideal but acceptable for builder's batch-insert path).
        if neo4j_client.is_connected and neo4j_client._driver:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in an async context — schedule as a task
                    asyncio.ensure_future(self._neo4j_upsert_node(node_id, labels, props))
                else:
                    loop.run_until_complete(self._neo4j_upsert_node(node_id, labels, props))
            except Exception as e:
                logger.debug(f"Neo4j upsert_node fallback: {e}")

    async def _neo4j_upsert_node(
        self, node_id: str, labels: List[str], props: Dict[str, Any]
    ) -> None:
        label_str = ":".join(labels) if labels else "Entity"
        async with neo4j_client._driver.session() as session:
            await session.run(
                f"MERGE (n:{label_str} {{id: $id}}) SET n += $props",
                id=node_id, props=props,
            )

    def upsert_edge(self, src: str, tgt: str, rel_type: str, props: Dict[str, Any]) -> None:
        case_id = props.get("case_id", "unknown")
        neo4j_client._mem.add_edge(case_id, src, tgt, rel_type, props)

        if neo4j_client.is_connected and neo4j_client._driver:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._neo4j_upsert_edge(src, tgt, rel_type, props))
                else:
                    loop.run_until_complete(self._neo4j_upsert_edge(src, tgt, rel_type, props))
            except Exception as e:
                logger.debug(f"Neo4j upsert_edge fallback: {e}")

    async def _neo4j_upsert_edge(
        self, src: str, tgt: str, rel_type: str, props: Dict[str, Any]
    ) -> None:
        async with neo4j_client._driver.session() as session:
            await session.run(
                f"""
                MATCH (a {{id: $src}}), (b {{id: $tgt}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $props
                """,
                src=src, tgt=tgt, props=props,
            )

    def get_graph_summary(self, case_id: str) -> Dict[str, Any]:
        return neo4j_client._mem.summary(case_id)

    def cleanup(self, case_id: str) -> None:
        neo4j_client._mem.clear(case_id)
        logger.info(f"Graph cleanup complete for case {case_id}")


# ── GraphBuilder with LLM extraction ────────────────────────────────────

EXTRACT_TRIPLES_PROMPT = """Extract knowledge graph triples from this evidence text.

TEXT:
{text}

Return JSON array of triples:
[
  {{
    "subject": {{"id": "...", "type": "person|location|evidence|event", "name": "..."}},
    "predicate": "...",
    "object": {{"id": "...", "type": "...", "name": "..."}},
    "certainty": 0.0-1.0
  }}
]"""


class GraphBuilder:
    """Orchestrates LLM extraction → graph storage."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self.storage = CrimeScopeGraphStorage()

    async def build_from_text(self, text: str) -> int:
        """Extract triples from text via LLM and store in graph."""
        prompt = EXTRACT_TRIPLES_PROMPT.format(text=text[:4000])
        raw = await openrouter.chat(
            settings.fast_model_name,
            prompt,
            system="You are a knowledge graph extraction engine. Return only JSON.",
        )

        parsed = ModelRouter.parse_json_safe(raw)
        if not parsed:
            logger.warning("GraphBuilder: failed to parse LLM triples")
            return 0

        triples = parsed if isinstance(parsed, list) else parsed.get("triples", [])
        count = 0
        for triple in triples:
            subj = triple.get("subject", {})
            obj = triple.get("object", {})
            pred = triple.get("predicate", "RELATED_TO")
            certainty = float(triple.get("certainty", 0.5))

            self.storage.upsert_node(
                subj.get("id", subj.get("name", "")),
                [subj.get("type", "Entity")],
                {"name": subj.get("name", ""), "case_id": self.case_id, "certainty": certainty},
            )
            self.storage.upsert_node(
                obj.get("id", obj.get("name", "")),
                [obj.get("type", "Entity")],
                {"name": obj.get("name", ""), "case_id": self.case_id, "certainty": certainty},
            )
            self.storage.upsert_edge(
                subj.get("id", subj.get("name", "")),
                obj.get("id", obj.get("name", "")),
                pred.upper().replace(" ", "_"),
                {"certainty": certainty, "case_id": self.case_id},
            )
            count += 1

        logger.info(f"GraphBuilder: stored {count} triples for case {self.case_id}")
        return count

    def build_from_seed(self, seed_packet: Dict[str, Any]) -> None:
        """Synchronously build graph nodes from the seed packet entities."""
        entities = seed_packet.get("entities", [])
        for ent in entities:
            self.storage.upsert_node(
                ent.get("name", ""),
                [ent.get("type", "Entity")],
                {
                    "name": ent.get("name", ""),
                    "description": ent.get("description", ""),
                    "case_id": self.case_id,
                    "certainty": ent.get("confidence", 0.5),
                },
            )

    def get_summary(self) -> Dict[str, Any]:
        return self.storage.get_graph_summary(self.case_id)

    def cleanup(self) -> None:
        self.storage.cleanup(self.case_id)

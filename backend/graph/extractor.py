"""
CRIMESCOPE v2 — Chunked entity + relationship extraction for knowledge graph.

Design:
1. Split document into overlapping chunks (max 3000 tokens each).
2. Extract entities from each chunk in parallel (semaphore-bounded).
3. Merge and deduplicate entities across chunks.
4. Extract relationships in a second LLM pass over the merged entity set.
5. Return a clean KnowledgeGraph for use in agent persona generation.
"""

from __future__ import annotations

import asyncio
import json
import re

import structlog

from core.llm import call_llm
from core.config import get_settings

log = structlog.get_logger("crimescope.graph")


# ── Data structures ──────────────────────────────────────────

class Entity:
    __slots__ = ("name", "type", "description", "aliases")

    def __init__(self, name: str, type: str, description: str = "", aliases: list[str] | None = None):
        self.name = name
        self.type = type
        self.description = description
        self.aliases = aliases or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "aliases": self.aliases,
        }


class Relationship:
    __slots__ = ("source", "target", "type", "description", "weight")

    def __init__(self, source: str, target: str, type: str, description: str = "", weight: float = 1.0):
        self.source = source
        self.target = target
        self.type = type
        self.description = description
        self.weight = weight

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "description": self.description,
            "weight": self.weight,
        }


class KnowledgeGraph:
    def __init__(self, entities: list[Entity] | None = None, relationships: list[Relationship] | None = None):
        self.entities = entities or []
        self.relationships = relationships or []

    @property
    def node_count(self) -> int:
        return len(self.entities)

    @property
    def edge_count(self) -> int:
        return len(self.relationships)

    def to_graph_data(self) -> dict:
        """Convert to frontend-consumable graph format."""
        nodes = []
        for i, e in enumerate(self.entities):
            nodes.append({
                "id": e.name,
                "name": e.name,
                "type": e.type,
                "description": e.description,
                "group": e.type,
                "index": i,
            })

        edges = []
        entity_names = {e.name for e in self.entities}
        for r in self.relationships:
            if r.source in entity_names and r.target in entity_names:
                edges.append({
                    "source": r.source,
                    "target": r.target,
                    "type": r.type,
                    "weight": r.weight,
                })

        return {"nodes": nodes, "edges": edges}


# ── Text chunking ────────────────────────────────────────────

def chunk_text(text: str, max_tokens: int = 3000, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks by approximate word count.
    Each "token" ≈ 1 word for estimation purposes.
    """
    words = text.split()
    if len(words) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        if start >= len(words):
            break

    return chunks


# ── Entity extraction (per chunk) ───────────────────────────

_ENTITY_PROMPT = """You are an expert knowledge graph builder analyzing a document about crime, society, or policy.

Extract all named entities from the text below. For each entity, provide:
- name: The canonical name
- type: One of [Person, Organization, Location, Event, Concept, Policy, Evidence, Weapon, Vehicle, Date]
- description: A one-sentence description

Return a JSON array of objects. Example:
[{"name": "John Doe", "type": "Person", "description": "Suspect in warehouse robbery."}]

TEXT:
{chunk}

Return ONLY the JSON array, no markdown fences."""


async def _extract_entities_from_chunk(
    chunk: str,
    semaphore: asyncio.Semaphore,
) -> list[Entity]:
    """Extract entities from a single text chunk."""
    async with semaphore:
        try:
            prompt = _ENTITY_PROMPT.format(chunk=chunk[:8000])
            raw = await call_llm(
                [{"role": "user", "content": prompt}],
                temperature=0.2,
                json_mode=True,
            )

            # Parse JSON from response
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?\s*", "", raw).rstrip("`")

            data = json.loads(raw)
            if isinstance(data, dict) and "entities" in data:
                data = data["entities"]

            entities = []
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    entities.append(Entity(
                        name=item["name"],
                        type=item.get("type", "Concept"),
                        description=item.get("description", ""),
                        aliases=item.get("aliases", []),
                    ))
            return entities

        except (json.JSONDecodeError, KeyError) as exc:
            log.warning("entity_parse_error", error=str(exc))
            return []
        except Exception as exc:
            log.error("entity_extraction_error", error=str(exc))
            return []


# ── Entity merging ───────────────────────────────────────────

def _merge_entities(chunk_results: list[list[Entity]]) -> list[Entity]:
    """Deduplicate entities across chunks by normalized name."""
    seen: dict[str, Entity] = {}
    for entities in chunk_results:
        for e in entities:
            key = e.name.strip().lower()
            if key in seen:
                # Merge: keep longer description
                existing = seen[key]
                if len(e.description) > len(existing.description):
                    existing.description = e.description
                existing.aliases = list(set(existing.aliases + e.aliases))
            else:
                seen[key] = e
    return list(seen.values())


# ── Relationship extraction ──────────────────────────────────

_REL_PROMPT = """You are a knowledge graph relationship extractor.

Given these entities: {entity_names}

And this document context:
{context}

Extract relationships between the entities. For each relationship, provide:
- source: Entity name (must be from the list)
- target: Entity name (must be from the list)
- type: Relationship type (e.g., "works_for", "located_in", "involved_in", "related_to")
- description: Brief description
- weight: Importance from 0.0 to 1.0

Return a JSON array. Example:
[{{"source": "John Doe", "target": "ACME Corp", "type": "works_for", "description": "Employee", "weight": 0.8}}]

Return ONLY the JSON array, no markdown fences."""


async def _extract_relationships(
    entities: list[Entity],
    context: str,
) -> list[Relationship]:
    """Extract relationships between merged entities."""
    if len(entities) < 2:
        return []

    entity_names = [e.name for e in entities[:80]]  # limit to avoid context overflow
    prompt = _REL_PROMPT.format(
        entity_names=json.dumps(entity_names),
        context=context[:6000],
    )

    try:
        raw = await call_llm(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            json_mode=True,
            boost=True,  # heavier task
        )

        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```(?:json)?\s*", "", raw).rstrip("`")

        data = json.loads(raw)
        if isinstance(data, dict) and "relationships" in data:
            data = data["relationships"]

        entity_set = {e.name for e in entities}
        relationships = []
        for item in data:
            if isinstance(item, dict) and "source" in item and "target" in item:
                if item["source"] in entity_set and item["target"] in entity_set:
                    relationships.append(Relationship(
                        source=item["source"],
                        target=item["target"],
                        type=item.get("type", "related_to"),
                        description=item.get("description", ""),
                        weight=float(item.get("weight", 0.5)),
                    ))
        return relationships

    except (json.JSONDecodeError, KeyError) as exc:
        log.warning("relationship_parse_error", error=str(exc))
        return []
    except Exception as exc:
        log.error("relationship_extraction_error", error=str(exc))
        return []


# ══════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════

async def extract_knowledge_graph(text: str) -> KnowledgeGraph:
    """
    Full pipeline: chunk → parallel entity extraction → merge → relationship extraction.

    Args:
        text: The full document text to process.

    Returns:
        A KnowledgeGraph with deduplicated entities and relationships.
    """
    settings = get_settings()
    semaphore = asyncio.Semaphore(settings.agent_concurrency)

    # 1. Chunk
    chunks = chunk_text(text, max_tokens=settings.graph_chunk_size, overlap=settings.graph_chunk_overlap)
    log.info("graph_chunked", chunks=len(chunks), text_len=len(text))

    # 2. Parallel entity extraction
    chunk_results = await asyncio.gather(
        *[_extract_entities_from_chunk(chunk, semaphore) for chunk in chunks],
        return_exceptions=True,
    )

    # Filter out exceptions
    valid_results = [r for r in chunk_results if isinstance(r, list)]
    log.info("graph_entities_extracted", chunk_results=len(valid_results))

    # 3. Merge
    entities = _merge_entities(valid_results)
    log.info("graph_entities_merged", count=len(entities))

    # 4. Relationships
    relationships = await _extract_relationships(entities, text)
    log.info("graph_relationships_extracted", count=len(relationships))

    return KnowledgeGraph(entities=entities, relationships=relationships)

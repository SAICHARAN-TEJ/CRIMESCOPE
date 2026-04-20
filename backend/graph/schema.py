# SPDX-License-Identifier: AGPL-3.0-only
"""
Typed Knowledge Graph schema — Pydantic models for nodes and edges.

Schema:
  Nodes: Person, Location, Event, Evidence, Document
  Edges: INVOLVED_IN, LOCATED_AT, MENTIONED_IN, CONTRADICTS,
         CORROBORATES, WITNESSED_BY, TIMELINE_BEFORE, TIMELINE_AFTER
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Node types ───────────────────────────────────────────────────────────

class NodeType(str, Enum):
    PERSON = "Person"
    LOCATION = "Location"
    EVENT = "Event"
    EVIDENCE = "Evidence"
    DOCUMENT = "Document"


class GraphNode(BaseModel):
    """Universal node representation in the knowledge graph."""

    id: str
    name: str
    node_type: NodeType
    case_id: str = ""
    properties: Dict[str, Any] = Field(default_factory=dict)
    certainty: float = Field(ge=0.0, le=1.0, default=0.5)
    embedding_id: Optional[str] = None  # Links to ChromaDB vector

    @property
    def label(self) -> str:
        return self.name


class PersonNode(GraphNode):
    node_type: NodeType = NodeType.PERSON
    role: str = ""  # victim, suspect, witness, associate
    credibility: float = Field(ge=0.0, le=1.0, default=0.5)
    aliases: List[str] = Field(default_factory=list)


class LocationNode(GraphNode):
    node_type: NodeType = NodeType.LOCATION
    location_type: str = ""  # indoor, outdoor, vehicle, digital
    coordinates: Optional[str] = None


class EventNode(GraphNode):
    node_type: NodeType = NodeType.EVENT
    timestamp: str = ""
    description: str = ""
    duration: Optional[str] = None


class EvidenceNode(GraphNode):
    node_type: NodeType = NodeType.EVIDENCE
    evidence_type: str = ""  # physical, digital, testimonial, forensic
    source_document: str = ""
    chain_of_custody: List[str] = Field(default_factory=list)


class DocumentNode(GraphNode):
    node_type: NodeType = NodeType.DOCUMENT
    document_type: str = ""  # police_report, witness_statement, forensic_report, video_transcript
    upload_time: str = ""
    page_count: int = 0


# ── Edge types ───────────────────────────────────────────────────────────

class EdgeType(str, Enum):
    INVOLVED_IN = "INVOLVED_IN"
    LOCATED_AT = "LOCATED_AT"
    MENTIONED_IN = "MENTIONED_IN"
    CONTRADICTS = "CONTRADICTS"
    CORROBORATES = "CORROBORATES"
    WITNESSED_BY = "WITNESSED_BY"
    TIMELINE_BEFORE = "TIMELINE_BEFORE"
    TIMELINE_AFTER = "TIMELINE_AFTER"
    CONNECTED_TO = "CONNECTED_TO"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    OWNS = "OWNS"
    WAS_AT = "WAS_AT"


class GraphEdge(BaseModel):
    """Directed relationship between two nodes."""

    source: str  # node ID
    target: str  # node ID
    edge_type: EdgeType
    case_id: str = ""
    properties: Dict[str, Any] = Field(default_factory=dict)
    certainty: float = Field(ge=0.0, le=1.0, default=0.5)
    discovered_in_round: int = 0


# ── Evidence Path (GraphRAG output) ─────────────────────────────────────

class EvidencePathStep(BaseModel):
    """Single step in a graph traversal path."""

    node: Dict[str, Any]
    edge: Optional[Dict[str, Any]] = None
    hop: int = 0


class EvidencePath(BaseModel):
    """A connected evidence chain through the knowledge graph.

    This is what GraphRAG returns instead of isolated text chunks.
    Each path represents a chain of connected entities/evidence
    with cumulative certainty scores.
    """

    steps: List[EvidencePathStep] = Field(default_factory=list)
    cumulative_certainty: float = 0.0
    path_description: str = ""

    @property
    def length(self) -> int:
        return len(self.steps)

    def summarize(self) -> str:
        """Human-readable path summary."""
        parts = []
        for s in self.steps:
            node = s.node
            parts.append(f"{node.get('name', '?')} ({node.get('type', '?')})")
            if s.edge:
                parts.append(f"—[{s.edge.get('type', '?')}]→")
        return " ".join(parts)


# ── Full Graph Snapshot ─────────────────────────────────────────────────

class GraphSnapshot(BaseModel):
    """Serialised graph for frontend D3 visualiser."""

    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    title: str = ""
    case_id: str = ""
    node_count: int = 0
    edge_count: int = 0

    def model_post_init(self, __context: Any) -> None:
        self.node_count = len(self.nodes)
        self.edge_count = len(self.edges)

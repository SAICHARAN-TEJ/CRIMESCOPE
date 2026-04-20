# SPDX-License-Identifier: AGPL-3.0-only
"""
Domain events for inter-component pub/sub.

Events are published to Redis (or in-memory) and consumed by
SSE streams and background workers.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    # Ingestion
    INGESTION_STARTED = "ingestion.started"
    INGESTION_PROGRESS = "ingestion.progress"
    INGESTION_COMPLETED = "ingestion.completed"
    INGESTION_FAILED = "ingestion.failed"

    # Agent pipeline
    AGENT_STARTED = "agent.started"
    AGENT_PROGRESS = "agent.progress"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # Simulation
    SIMULATION_STARTED = "simulation.started"
    SIMULATION_ROUND = "simulation.round"
    SIMULATION_COMPLETED = "simulation.completed"
    SIMULATION_FAILED = "simulation.failed"

    # Graph
    GRAPH_UPDATED = "graph.updated"
    GRAPH_TRAVERSAL = "graph.traversal"


class DomainEvent(BaseModel):
    """Wire format for all CrimeScope events."""

    event_type: EventType
    case_id: str = ""
    timestamp: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None

    def to_sse(self) -> str:
        """Serialise as a Server-Sent Event data line."""
        import json
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.payload)}\n\n"

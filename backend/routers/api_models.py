# SPDX-License-Identifier: AGPL-3.0-only
"""
Centralized Pydantic V2 API models for all CrimeScope endpoints.

All request/response models live here for consistency and
OpenAPI schema generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request Models ────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Chat endpoint request."""
    question: str = Field(..., min_length=1, max_length=2000, description="Question to ask about the case")


class SimulationStartRequest(BaseModel):
    """Start simulation request."""
    case_id: str
    num_agents: int = Field(default=1000, ge=10, le=10000)
    num_rounds: int = Field(default=30, ge=5, le=100)


# ── Response Models ───────────────────────────────────────────────────────

class AgentStatus(BaseModel):
    """Status of a single agent in the pipeline."""
    success: bool
    error: Optional[str] = None
    processing_time_ms: float = 0.0


class PipelineProgress(BaseModel):
    """SSE progress event for agent pipeline."""
    agent: str
    status: str  # started | completed | error | timeout
    elapsed_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class UploadResponse(BaseModel):
    """Response after evidence upload."""
    id: str = Field(..., description="Case ID")
    title: str
    mode: int
    status: str = "processing"
    stream_url: Optional[str] = Field(None, description="SSE URL for pipeline progress")
    seed_packet: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat endpoint response."""
    case_id: str
    question: str
    answer: str
    graph_paths: int = Field(default=0, description="Number of GraphRAG evidence paths used")
    rag_fragments: int = Field(default=0, description="Number of vector search results used")
    cached: bool = False


class HealthService(BaseModel):
    """Health check for a single service."""
    status: str  # ok | degraded | unavailable
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Full health check response."""
    status: str  # healthy | degraded | unhealthy
    version: str = "3.0.0"
    uptime_seconds: float
    services: Dict[str, HealthService] = Field(default_factory=dict)


class SynthesisReport(BaseModel):
    """Final synthesis report from the agent pipeline."""
    executive_summary: str = ""
    key_findings: List[str] = Field(default_factory=list)
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions_summary: str = ""
    recommended_actions: List[str] = Field(default_factory=list)
    overall_confidence: float = 0.0


class PipelineResult(BaseModel):
    """Complete result from the agent pipeline."""
    case_id: str
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    legal_findings: List[Dict[str, Any]] = Field(default_factory=list)
    synthesis_report: Optional[SynthesisReport] = None
    agent_statuses: Dict[str, AgentStatus] = Field(default_factory=dict)
    total_processing_time_ms: float = 0.0

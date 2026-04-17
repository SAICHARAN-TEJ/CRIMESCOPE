"""
CRIMESCOPE v2 — All Pydantic request/response schemas.

Single source of truth for the API contract between frontend and backend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════

class StartSimulationRequest(BaseModel):
    requirement: str = Field(..., min_length=10, max_length=2000)
    agent_count: int = Field(default=50, ge=5, le=500)
    max_rounds: int = Field(default=25, ge=1, le=100)
    platform: Literal["parallel", "twitter", "reddit"] = "parallel"


class ChatRequest(BaseModel):
    simulation_id: str
    agent_id: str  # "report" for ReportAgent, else agent UUID
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


class InjectVariableRequest(BaseModel):
    simulation_id: str
    content: str = Field(..., min_length=1, max_length=500)


# ══════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ══════════════════════════════════════════════════════════════

class SimulationStartResponse(BaseModel):
    simulation_id: str
    status: str = "initializing"


class SimulationStatusResponse(BaseModel):
    id: str
    status: str
    current_phase: str
    round: int = 0
    total_rounds: int
    agent_count: int = 0
    graph_node_count: int = 0
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentResponse(BaseModel):
    id: str
    name: str
    persona: str = ""
    archetype: str = ""
    faction: str = "neutral"
    stance: float = Field(default=0.0, ge=-1.0, le=1.0)
    influence: int = 0
    platform: str = "both"
    memory: list[str] = Field(default_factory=list)


class PostResponse(BaseModel):
    agent_id: str = ""
    agent_name: str = ""
    platform: str = "twitter"
    content: str = ""
    action_type: str = "post"
    timestamp: float = 0.0
    stance: str = "neutral"
    round_num: int = 0


class GraphResponse(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class ReportResponse(BaseModel):
    title: str = ""
    executive_summary: str = ""
    methodology: str = ""
    confidence: float = 0.0
    key_findings: list[dict] = Field(default_factory=list)
    factions: list[dict] = Field(default_factory=list)


class SimulationSummaryResponse(BaseModel):
    id: str
    status: str
    requirement: str = ""
    agent_count: int = 0
    round: int = 0
    total_rounds: int = 0
    created_at: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "CRIMESCOPE Backend v2"
    uptime_s: float = 0.0


class ErrorResponse(BaseModel):
    detail: str

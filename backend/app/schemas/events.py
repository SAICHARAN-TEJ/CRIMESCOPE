"""
CrimeScope — Pydantic Event & API Models.

All WebSocket events, API requests/responses, and internal DTOs.
Strictly typed for OpenAPI generation and runtime validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────


class AgentType(str, Enum):
    VIDEO = "video"
    DOCUMENT = "document"
    ENTITY = "entity"
    GRAPH = "graph"
    SUPERVISOR = "supervisor"


class EventType(str, Enum):
    """Events published to Redis and forwarded via WebSocket."""
    JOB_STARTED = "JOB_STARTED"
    AGENT_START = "AGENT_START"
    AGENT_PROGRESS = "AGENT_PROGRESS"
    AGENT_COMPLETE = "AGENT_COMPLETE"
    AGENT_ERROR = "AGENT_ERROR"
    GRAPH_NODE_ADD = "GRAPH_NODE_ADD"
    GRAPH_EDGE_ADD = "GRAPH_EDGE_ADD"
    PIPELINE_COMPLETE = "PIPELINE_COMPLETE"
    HEARTBEAT = "HEARTBEAT"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ── WebSocket / Redis Events ──────────────────────────────────────────────


class WSEvent(BaseModel):
    """Event published to Redis and forwarded to frontend via WebSocket."""
    event: EventType
    job_id: str
    agent: Optional[AgentType] = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = None


class GraphNodeEvent(BaseModel):
    """Payload for GRAPH_NODE_ADD events."""
    id: str
    label: str
    type: str  # person, location, event, evidence
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeEvent(BaseModel):
    """Payload for GRAPH_EDGE_ADD events."""
    source: str
    target: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


# ── API Request Models ────────────────────────────────────────────────────


class UploadInitRequest(BaseModel):
    """Request to get a pre-signed upload URL from MinIO."""
    filename: str
    content_type: str = "application/octet-stream"


class UploadCompleteRequest(BaseModel):
    """Notify backend that upload to MinIO is done."""
    object_key: str
    filename: str
    content_type: str
    file_size: int = 0


class AnalysisStartRequest(BaseModel):
    """Start a new analysis job."""
    job_id: str = Field(default_factory=lambda: uuid4().hex)
    files: list[UploadCompleteRequest]
    question: str = ""


class LoginRequest(BaseModel):
    """Login credentials."""
    username: str
    password: str


# ── API Response Models ───────────────────────────────────────────────────


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PresignedURLResponse(BaseModel):
    """Pre-signed URL for direct-to-MinIO upload."""
    upload_url: str
    object_key: str
    expires_in: int = 3600


class JobResponse(BaseModel):
    """Job creation response."""
    job_id: str
    status: JobStatus
    ws_url: str


class HealthResponse(BaseModel):
    """System health check."""
    status: str
    version: str = "4.0.0"
    services: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Result from a single agent."""
    agent: AgentType
    success: bool
    processing_time_ms: float = 0.0
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class PipelineResult(BaseModel):
    """Full pipeline result."""
    job_id: str
    status: JobStatus
    agents: list[AgentResult] = Field(default_factory=list)
    total_entities: int = 0
    total_relationships: int = 0
    total_processing_time_ms: float = 0.0

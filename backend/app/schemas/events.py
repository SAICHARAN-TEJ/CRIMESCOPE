"""
CrimeScope — Pydantic Event & API Models.

All WebSocket events, API requests/responses, and internal DTOs.
Strictly typed for OpenAPI generation and runtime validation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# ── Enums ─────────────────────────────────────────────────────────────────


class AgentType(str, Enum):
    VIDEO = "video"
    DOCUMENT = "document"
    ENTITY = "entity"
    GRAPH = "graph"
    SUPERVISOR = "supervisor"
    PERSONA = "persona"
    REPORT = "report"
    CONSENSUS = "consensus"
    SCENARIO = "scenario"


class EventType(str, Enum):
    """Events published to Redis and forwarded via WebSocket."""
    CONNECTED = "CONNECTED"
    JOB_STARTED = "JOB_STARTED"
    AGENT_START = "AGENT_START"
    AGENT_PROGRESS = "AGENT_PROGRESS"
    AGENT_COMPLETE = "AGENT_COMPLETE"
    AGENT_ERROR = "AGENT_ERROR"
    GRAPH_NODE_ADD = "GRAPH_NODE_ADD"
    GRAPH_EDGE_ADD = "GRAPH_EDGE_ADD"
    PIPELINE_COMPLETE = "PIPELINE_COMPLETE"
    HEARTBEAT = "HEARTBEAT"
    BATCH_UPDATE = "BATCH_UPDATE"
    # ── Observable Investigation Events (contract docs/OBSERVABLE_CONTRACT.md) ─
    STAGE_UPDATE = "STAGE_UPDATE"
    ACTIVITY = "ACTIVITY"
    DECOMP_UPDATE = "DECOMP_UPDATE"
    AGENT_WAITING = "AGENT_WAITING"
    # ── Swarm Intelligence Events ─────────────────────────────────
    PERSONA_INSIGHT = "PERSONA_INSIGHT"
    REPORT_CHUNK = "REPORT_CHUNK"
    CONSENSUS_RESULT = "CONSENSUS_RESULT"
    SCENARIO_DIFF = "SCENARIO_DIFF"
    SCENARIO_EVAL = "SCENARIO_EVAL"


class StageState(str, Enum):
    """Lifecycle states for observable pipeline stages."""
    QUEUED = "QUEUED"
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class DecompState(str, Enum):
    """Lifecycle states for an individual evidence decomposition step."""
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"
    FAILED = "failed"


class ActivityLevel(str, Enum):
    """Semantic severity used by the operations activity stream."""
    INFO = "info"
    SUCCESS = "success"
    WARN = "warn"
    ERROR = "error"


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
    agent: AgentType | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    correlation_id: str | None = None


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


# ── Observable Investigation Payloads (docs/OBSERVABLE_CONTRACT.md §3) ────
# Lax validation (default model config) on purpose: these payloads cross the
# Redis→WS JSON boundary as plain strings/dicts, matching every other model
# in this module. The only hard bound is ActivityData.text (≤120 chars).


class StageUpdateData(BaseModel):
    """Payload for STAGE_UPDATE events — one pipeline stage transition."""
    stage: str = Field(max_length=32)
    state: StageState
    label: str = Field(max_length=64)
    detail: str = Field(default="", max_length=255)
    agents: list[str] = Field(default_factory=list)
    item_count: int | None = Field(default=None, ge=0)
    started_at: str | None = None
    completed_at: str | None = None


class ActivityData(BaseModel):
    """Payload for ACTIVITY events — one semantic activity-stream line."""
    actor: str = Field(min_length=1, max_length=32)
    stage: str = Field(min_length=1, max_length=32)
    text: str = Field(max_length=120)
    level: ActivityLevel = ActivityLevel.INFO
    metrics: dict[str, Any] | None = None


class DecompUpdateData(BaseModel):
    """Payload for DECOMP_UPDATE events — per-evidence decomposition step."""
    evidence_id: str = Field(min_length=1, max_length=255)
    filename: str = Field(min_length=1, max_length=255)
    step: str = Field(min_length=1, max_length=64)
    state: DecompState
    detail: str = Field(default="", max_length=255)
    progress: dict[str, Any] | None = None  # {current, total} — real counts only


class AgentWaitingData(BaseModel):
    """Payload for AGENT_WAITING — explicit dependency telemetry."""
    agent: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=255)
    upstream: list[dict[str, str]] = Field(default_factory=list)
    expected_next: str | None = Field(default=None, max_length=64)


# ── API Request Models ────────────────────────────────────────────────────


class UploadInitRequest(BaseModel):
    """Request to get a pre-signed upload URL from MinIO."""
    filename: str = Field(max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=128)


class UploadCompleteRequest(BaseModel):
    """Notify backend that upload to MinIO is done."""
    object_key: str = Field(max_length=512)
    filename: str = Field(max_length=255)
    content_type: str = Field(max_length=128)
    file_size: int = Field(default=0, ge=0)


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
    version: str = "4.4.0"
    services: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Result from a single agent."""
    agent: AgentType
    success: bool
    processing_time_ms: float = 0.0
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    error: str | None = None


class PipelineResult(BaseModel):
    """Full pipeline result."""
    job_id: str
    status: JobStatus
    agents: list[AgentResult] = Field(default_factory=list)
    total_entities: int = 0
    total_relationships: int = 0
    total_processing_time_ms: float = 0.0


# ── Swarm Intelligence Models ─────────────────────────────────────────────


class PersonaConfig(BaseModel):
    """Definition of an investigative persona."""
    name: str
    role: str
    system_prompt: str
    expertise_tags: list[str] = Field(default_factory=list)
    temperature: float = 0.7


class PersonaInsightEvent(BaseModel):
    """Payload for PERSONA_INSIGHT events."""
    persona_name: str
    persona_role: str
    insight: str
    confidence: float = 0.0
    follow_up_questions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Request to send a question to the ReportAgent or a materialized persona."""
    job_id: str
    message: str
    conversation_id: str | None = None
    persona_id: str | None = None  # set to interview a graph-entity persona


class ChatResponse(BaseModel):
    """Response from the ReportAgent."""
    conversation_id: str
    message: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    persona_id: str | None = None


class PersonaMaterialized(BaseModel):
    """A materialized graph-entity persona."""
    persona_id: str
    name: str
    role: str
    evidence_refs: list[str] = Field(default_factory=list)
    grounded_nodes: int = Field(default=1, description="Number of supporting graph nodes")
    statements: list[str] = Field(default_factory=list)


class PersonaMaterializeResponse(BaseModel):
    """Result of POST /analysis/{job_id}/personas."""
    job_id: str
    personas: list[PersonaMaterialized]
    count: int
    total_person_nodes: int


class ScenarioRequest(BaseModel):
    """Inject a hypothesis scenario for evaluation."""
    job_id: str
    hypothesis: str


class ScenarioEvaluation(BaseModel):
    """A single persona's evaluation of a scenario."""
    persona_name: str
    verdict: str  # supports | contradicts | neutral
    reasoning: str
    confidence: float = 0.0


class ScenarioResult(BaseModel):
    """Full result of a scenario hypothesis evaluation."""
    scenario_id: str
    hypothesis: str
    evaluations: list[ScenarioEvaluation] = Field(default_factory=list)
    new_entities: list[GraphNodeEvent] = Field(default_factory=list)
    new_edges: list[GraphEdgeEvent] = Field(default_factory=list)
    removed_entities: list[dict] = Field(default_factory=list)
    removed_edges: list[dict] = Field(default_factory=list)
    consensus_verdict: str = "pending"  # supports | contradicts | neutral | mixed
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

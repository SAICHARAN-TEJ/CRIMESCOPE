/**
 * CrimeScope — TypeScript Type Definitions.
 *
 * Mirrors backend Pydantic models for end-to-end type safety.
 */

// ── Enums ────────────────────────────────────────────────────────────────

export enum AgentType {
  VIDEO = "video",
  DOCUMENT = "document",
  ENTITY = "entity",
  GRAPH = "graph",
  SUPERVISOR = "supervisor",
}

export enum EventType {
  JOB_STARTED = "JOB_STARTED",
  AGENT_START = "AGENT_START",
  AGENT_PROGRESS = "AGENT_PROGRESS",
  AGENT_COMPLETE = "AGENT_COMPLETE",
  AGENT_ERROR = "AGENT_ERROR",
  GRAPH_NODE_ADD = "GRAPH_NODE_ADD",
  GRAPH_EDGE_ADD = "GRAPH_EDGE_ADD",
  PIPELINE_COMPLETE = "PIPELINE_COMPLETE",
  HEARTBEAT = "HEARTBEAT",
  CONNECTED = "CONNECTED",
}

export enum JobStatus {
  QUEUED = "queued",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  PARTIAL = "partial",
}

// ── WebSocket Events ─────────────────────────────────────────────────────

export interface WSEvent {
  event: EventType | string;
  job_id: string;
  agent?: AgentType;
  data: Record<string, unknown>;
  timestamp?: string;
}

// ── Graph Types ──────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  properties: Record<string, unknown>;
}

// ── Agent State ──────────────────────────────────────────────────────────

export interface AgentStatus {
  type: AgentType;
  status: "idle" | "running" | "complete" | "error";
  processingTimeMs: number;
  entityCount: number;
  error?: string;
}

// ── API Types ────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface PresignedURLResponse {
  upload_url: string;
  object_key: string;
  expires_in: number;
}

export interface UploadFile {
  object_key: string;
  filename: string;
  content_type: string;
  file_size: number;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  ws_url: string;
}

// ── Vis.js Node/Edge (for vis-network) ───────────────────────────────────

export interface VisNode {
  id: string;
  label: string;
  group: string;
  title?: string;
  size?: number;
}

export interface VisEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  arrows: string;
}

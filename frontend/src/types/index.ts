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
  PERSONA = "persona",
  REPORT = "report",
  CONSENSUS = "consensus",
  SCENARIO = "scenario",
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
  BATCH_UPDATE = "BATCH_UPDATE",
  PERSONA_INSIGHT = "PERSONA_INSIGHT",
  REPORT_CHUNK = "REPORT_CHUNK",
  CONSENSUS_RESULT = "CONSENSUS_RESULT",
  SCENARIO_EVAL = "SCENARIO_EVAL",
  SCENARIO_DIFF = "SCENARIO_DIFF",
  STAGE_UPDATE = "STAGE_UPDATE",
  ACTIVITY = "ACTIVITY",
  DECOMP_UPDATE = "DECOMP_UPDATE",
  AGENT_WAITING = "AGENT_WAITING",
}

export enum JobStatus {
  QUEUED = "queued",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  PARTIAL = "partial",
}

// ── Observable investigation pipeline ────────────────────────────────────

export const PIPELINE_STAGE_IDS = [
  "ingest",
  "triage",
  "extract",
  "understand",
  "connect",
  "challenge",
  "verify",
  "report",
] as const

export type PipelineStage = typeof PIPELINE_STAGE_IDS[number]

export type StageState =
  | "QUEUED"
  | "ACTIVE"
  | "WAITING"
  | "BLOCKED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "SKIPPED"

export type DecompState = "pending" | "active" | "done" | "failed"
export type ActivityLevel = "info" | "success" | "warn" | "error"

export interface StageUpdate {
  stage: string
  state: StageState
  label: string
  detail?: string
  agents?: string[]
  item_count?: number | null
  started_at?: string | null
  completed_at?: string | null
}

export interface ActivityEvent {
  actor: string
  stage: string
  text: string
  level?: ActivityLevel | string
  metrics?: Record<string, unknown> | null
}

export interface DecompProgress {
  current: number
  total: number
}

export interface DecompUpdate {
  evidence_id: string
  filename: string
  step: string
  state: DecompState
  detail?: string
  progress?: DecompProgress | null
}

export interface AgentWaitingEvent {
  agent: string
  reason: string
  upstream?: Array<{ agent: string; status: string }>
  expected_next?: string | null
}

export interface StageRuntime {
  stage: string
  state: StageState
  label: string
  detail: string
  agents: string[]
  itemCount: number | null
  startedAt: string | null
  completedAt: string | null
  elapsedMs: number
}

export interface DecompStepRuntime {
  step: string
  state: DecompState
  detail: string
  progress: DecompProgress | null
  updatedAt: string
  history: Array<{
    state: DecompState
    detail: string
    progress: DecompProgress | null
    timestamp: string
  }>
}

export interface EvidenceRuntime {
  evidenceId: string
  filename: string
  contentType?: string
  sizeBytes?: number
  hashVerified?: boolean
  steps: Record<string, DecompStepRuntime>
  firstSeenAt: string
  updatedAt: string
}

export interface ActivityRuntime {
  id: string
  actor: string
  stage: string
  text: string
  level: ActivityLevel
  timestamp: string
}

// ── WebSocket Events ─────────────────────────────────────────────────────

export interface WSEvent {
  event: EventType | string;
  job_id: string;
  agent?: AgentType;
  data: Record<string, unknown>;
  timestamp?: string;
  sequence?: number;
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
  type: AgentType | string;
  status: "idle" | "running" | "waiting" | "complete" | "error";
  processingTimeMs: number;
  entityCount: number;
  error?: string;
  waitingReason?: string;
  waitingFor?: Array<{ agent: string; status: string }>;
}

// ── Swarm Data Types ─────────────────────────────────────────────────────

export interface PersonaProfile {
  id: string;
  name: string;
  role: string;
  motivation: string;
  background: string;
  bias?: string;
}

/** PERSONA_INSIGHT event payload (§14 final vocabulary). */
export interface PersonaInsight {
  persona_id: string;
  persona_name: string;
  insight: string;
  confidence: number;
  evidence_refs?: string[];
  nodes_referenced?: string[];
}

/** A single persona's evaluation of a scenario hypothesis. */
export interface ScenarioEvaluation {
  persona_name: string;
  verdict: string; // supports | contradicts | neutral
  reasoning: string;
  confidence: number;
}

/**
 * SCENARIO_DIFF payload (§14 final vocabulary).
 * `insights` are derived client-side from `evaluations`.
 */
export interface ScenarioDiff {
  scenario_id: string;
  consensus_verdict?: string; // supports | contradicts | neutral | mixed | pending
  new_entities: GraphNode[];
  new_edges: GraphEdge[];
  removed_edges?: GraphEdge[];
  evaluations?: ScenarioEvaluation[];
  insights: string[];
}

export interface ConsensusResult {
  agreement: string;
  disagreement: string;
  synthesis: string;
}

/** Chat roles are pinned to "assistant" (§15) — never "agent". */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
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

/** Response from POST /chat (ChatResponse in the backend schema). */
export interface ChatResponse {
  conversation_id: string;
  message: string;
  sources: string[];
  confidence: number;
  persona_id?: string | null;
}

/** A materialized graph-entity persona from POST /analysis/{job_id}/personas. */
export interface MaterializedPersona {
  persona_id: string;
  name: string;
  role: string;
  evidence_refs: string[];
  grounded_nodes: number;
  statements: string[];
}

/** Response from POST /analysis/{job_id}/personas (PersonaMaterializeResponse). */
export interface PersonaMaterializeResponse {
  job_id: string;
  personas: MaterializedPersona[];
  count: number;
  total_person_nodes: number;
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

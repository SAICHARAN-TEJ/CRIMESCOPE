// types/crimescope.ts — CRIMESCOPE Core TypeScript Interfaces

export type ThreatLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'CLEARED';

export type SimulationPhase =
  | 'SEED_UPLOAD'
  | 'GRAPH_BUILD'
  | 'AGENT_CONFIG'
  | 'SIMULATION'
  | 'REPORT_READY';

export type EntityType =
  | 'SUSPECT'
  | 'LEA'
  | 'WITNESS'
  | 'LOCATION'
  | 'ORGANIZATION'
  | 'EVIDENCE';

export type EventSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type AgentRole = 'SUSPECT' | 'LEA' | 'WITNESS' | 'ANALYST' | 'COMMUNITY';

export type SimulationSpeed = '1x' | '5x' | '10x' | 'MAX';

// ── Case Session ──────────────────────────────────────────────
export interface CaseSession {
  id: string;
  caseNumber: string;
  scenarioTitle: string;
  description: string;
  phase: SimulationPhase;
  threatLevel: ThreatLevel;
  agentCount: number;
  roundsCompleted: number;
  totalRounds: number;
  confidence: number;
  elapsedTime: string;
  createdAt: string;
  updatedAt: string;
  jurisdiction: string;
  tags: string[];
}

// ── Graph Entity ──────────────────────────────────────────────
export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  role?: AgentRole;
  confidence: number;
  centrality: number;
  description: string;
  attributes: Record<string, string | number | boolean>;
  connections: string[]; // entity IDs
  locationLat?: number;
  locationLng?: number;
  metadata: {
    firstSeen: string;
    lastActive: string;
    incidentCount: number;
  };
}

// ── Graph Edge ────────────────────────────────────────────────
export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  strength: number; // 0..1
  confidence: number;
  verified: boolean;
}

// ── Simulation Agent ──────────────────────────────────────────
export interface SimAgent {
  id: string;
  name: string;
  role: AgentRole;
  x: number;
  y: number;
  targetX: number;
  targetY: number;
  state: 'IDLE' | 'MOVING' | 'INTERACTING' | 'ALERT';
  threatScore: number; // 0..100
  round: number;
  lastAction: string;
}

// ── Simulation Event ──────────────────────────────────────────
export interface SimulationEvent {
  timestamp: string;
  round: number;
  agentId: string;
  agentRole: AgentRole;
  eventType: 'MOVEMENT' | 'INTERACTION' | 'ALERT' | 'PATROL' | 'REPORT' | 'EVIDENCE';
  description: string;
  severity: EventSeverity;
  location?: string;
  targetAgentId?: string;
}

// ── Intel Report ──────────────────────────────────────────────
export interface IntelReport {
  id: string;
  sessionId: string;
  title: string;
  generatedAt: string;
  confidence: number;
  threatLevel: ThreatLevel;

  executiveSummary: string;

  riskMatrix: RiskMatrixItem[];

  timeline: TimelineEvent[];

  keyActors: ActorProfile[];

  recommendedActions: RecommendedAction[];

  confidenceMetadata: {
    dataQuality: number;
    modelCoverage: number;
    simulationDepth: number;
    evidenceStrength: number;
  };

  sections: ReportSection[];
}

export interface RiskMatrixItem {
  id: string;
  label: string;
  likelihood: number; // 1..5
  impact: number;     // 1..5
  current: boolean;
}

export interface TimelineEvent {
  date: string;
  label: string;
  type: 'PAST' | 'PRESENT' | 'PREDICTED';
  confidence: number;
  description: string;
}

export interface ActorProfile {
  entityId: string;
  name: string;
  role: EntityType;
  threatScore: number;
  bio: string;
  keyActions: string[];
  connections: number;
}

export interface RecommendedAction {
  id: number;
  priority: 'IMMEDIATE' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  assignedTo: string;
  deadline: string;
}

export interface ReportSection {
  id: string;
  title: string;
  content: string;
  confidence: number;
}

// ── Chat Message ──────────────────────────────────────────────
export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: string;
  agentId?: string;
  agentName?: string;
}

// ── Variable Injection ────────────────────────────────────────
export interface InjectionVariable {
  id: string;
  label: string;
  description: string;
  type: 'slider' | 'toggle' | 'select';
  min?: number;
  max?: number;
  step?: number;
  value: number | boolean | string;
  unit?: string;
  options?: string[];
}

// ── API Response Wrappers ─────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  task_id?: string;
}

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: Record<string, unknown>;
  error?: string;
}

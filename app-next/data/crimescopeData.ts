// data/crimescopeData.ts — Mock data and system constants
import type {
  CaseSession, SimulationEvent, Entity, IntelReport,
  InjectionVariable, ThreatLevel, SimulationPhase, EntityType
} from '@/types/crimescope';

// ── Phase Labels ──────────────────────────────────────────────
export const PHASE_LABELS: Record<SimulationPhase, string> = {
  SEED_UPLOAD:  'SEED UPLOAD',
  GRAPH_BUILD:  'GRAPH BUILD',
  AGENT_CONFIG: 'AGENT CONFIG',
  SIMULATION:   'SIMULATION',
  REPORT_READY: 'REPORT READY',
};

// ── Threat Colors ─────────────────────────────────────────────
export const THREAT_COLORS: Record<ThreatLevel, { text: string; bg: string; border: string }> = {
  CRITICAL: { text: '#C62828', bg: 'rgba(198,40,40,0.15)',   border: 'rgba(198,40,40,0.4)' },
  HIGH:     { text: '#F57F17', bg: 'rgba(245,127,23,0.12)',  border: 'rgba(245,127,23,0.35)' },
  MEDIUM:   { text: '#F9A825', bg: 'rgba(249,168,37,0.10)',  border: 'rgba(249,168,37,0.30)' },
  LOW:      { text: '#78909C', bg: 'rgba(120,144,156,0.10)', border: 'rgba(120,144,156,0.25)' },
  CLEARED:  { text: '#2E7D32', bg: 'rgba(46,125,50,0.10)',   border: 'rgba(46,125,50,0.30)' },
};

// ── Entity Colors ─────────────────────────────────────────────
export const ENTITY_COLORS: Record<EntityType, string> = {
  SUSPECT:      '#C62828',
  LEA:          '#0D47A1',
  WITNESS:      '#37474F',
  LOCATION:     '#F57F17',
  ORGANIZATION: '#2E7D32',
  EVIDENCE:     '#00BCD4',
};

// ── System strings for live feed ─────────────────────────────
export const SYSTEM_STRINGS = [
  'GRAPH TOPOLOGY STABLE',
  'AGENTS NOMINAL — 2,847 ACTIVE',
  'THREAT NETWORK: 3 CLUSTERS',
  'SIMULATION ROUND 142/200',
  'EVIDENCE NODES: 31 CONFIRMED',
  'LEA COORDINATION: ACTIVE',
  'SUSPECT CONVERGENCE: 74%',
  'INTELLIGENCE PIPELINE: NOMINAL',
  'COMMS INTERCEPT: PROCESSING',
  'HOTSPOT DELTA: +12% SECTOR 4',
];

// ── Mock Sessions ─────────────────────────────────────────────
export const MOCK_SESSIONS: CaseSession[] = [
  {
    id: 'CS-2847',
    caseNumber: 'CS-2847',
    scenarioTitle: 'Narcotics Network — Downtown Sector 4',
    description: 'Multi-agency investigation into suspected fentanyl distribution network operating across downtown corridors.',
    phase: 'SIMULATION',
    threatLevel: 'CRITICAL',
    agentCount: 2847,
    roundsCompleted: 142,
    totalRounds: 200,
    confidence: 0,
    elapsedTime: '4h 17m',
    createdAt: '2026-04-17T08:00:00Z',
    updatedAt: '2026-04-17T12:17:00Z',
    jurisdiction: 'Metro PD District 4',
    tags: ['narcotics', 'multi-agency', 'urban'],
  },
  {
    id: 'CS-2831',
    caseNumber: 'CS-2831',
    scenarioTitle: 'Financial Fraud — Shell Corporation Ring',
    description: 'Investigation into suspected shell company network laundering proceeds from organized crime.',
    phase: 'REPORT_READY',
    threatLevel: 'HIGH',
    agentCount: 1204,
    roundsCompleted: 200,
    totalRounds: 200,
    confidence: 87,
    elapsedTime: '11h 42m',
    createdAt: '2026-04-16T14:00:00Z',
    updatedAt: '2026-04-17T01:42:00Z',
    jurisdiction: 'Financial Crimes Unit',
    tags: ['financial', 'corporate', 'laundering'],
  },
  {
    id: 'CS-2819',
    caseNumber: 'CS-2819',
    scenarioTitle: 'Gang Activity — Westside Territorial Dispute',
    description: 'Predictive analysis of escalating territorial conflict between known organized groups.',
    phase: 'GRAPH_BUILD',
    threatLevel: 'HIGH',
    agentCount: 489,
    roundsCompleted: 0,
    totalRounds: 150,
    confidence: 0,
    elapsedTime: '22m',
    createdAt: '2026-04-17T12:30:00Z',
    updatedAt: '2026-04-17T12:52:00Z',
    jurisdiction: 'Gang Crimes Division',
    tags: ['gang', 'territorial', 'violence'],
  },
];

// ── Mock Events ───────────────────────────────────────────────
export const MOCK_EVENTS: SimulationEvent[] = [
  {
    timestamp: '12:17:43',
    round: 142,
    agentId: 'AGENT_047',
    agentRole: 'SUSPECT',
    eventType: 'MOVEMENT',
    description: 'SUSPECT_047 [PHANTOM] relocated from SECTOR_4 to SECTOR_7 — evading last known LEA position.',
    severity: 'HIGH',
  },
  {
    timestamp: '12:17:31',
    round: 142,
    agentId: 'LEA_012',
    agentRole: 'LEA',
    eventType: 'PATROL',
    description: 'LEA_012 [UNIT 7-ALPHA] established observation post at NODE_218. Coverage radius 400m.',
    severity: 'LOW',
  },
  {
    timestamp: '12:17:18',
    round: 141,
    agentId: 'AGENT_089',
    agentRole: 'SUSPECT',
    eventType: 'INTERACTION',
    description: 'INTERACTION detected — AGENT_089 contacted AGENT_023 via encrypted channel. Probability: 94%.',
    severity: 'CRITICAL',
  },
  {
    timestamp: '12:17:02',
    round: 141,
    agentId: 'WIT_004',
    agentRole: 'WITNESS',
    eventType: 'REPORT',
    description: 'WITNESS_004 submitted location report — WAREHOUSE_DELTA active between 02:00-04:00 local.',
    severity: 'MEDIUM',
  },
  {
    timestamp: '12:16:55',
    round: 141,
    agentId: 'AGENT_031',
    agentRole: 'SUSPECT',
    eventType: 'ALERT',
    description: 'ALERT: AGENT_031 behavioral anomaly — deviation 3.2σ from baseline. Possible compromise.',
    severity: 'HIGH',
  },
  {
    timestamp: '12:16:40',
    round: 141,
    agentId: 'LEA_003',
    agentRole: 'LEA',
    eventType: 'PATROL',
    description: 'LEA_003 [UNIT 3-BRAVO] reporting corridor clear. Next sweep T+8m.',
    severity: 'LOW',
  },
];

// ── Mock Entities ─────────────────────────────────────────────
export const MOCK_ENTITIES: Entity[] = [
  {
    id: 'e001',
    name: 'PHANTOM (Viktor R.)',
    type: 'SUSPECT',
    confidence: 91,
    centrality: 0.87,
    description: 'Primary coordinator. Controls distribution network across 3 sectors. Known associates: 14.',
    attributes: { age: 34, nationality: 'Unknown', priors: 2, threat_score: 94 },
    connections: ['e002', 'e003', 'e007', 'e008'],
    metadata: { firstSeen: '2026-02-14', lastActive: '2026-04-17', incidentCount: 23 },
  },
  {
    id: 'e002',
    name: 'WRAITH (Marco L.)',
    type: 'SUSPECT',
    confidence: 78,
    centrality: 0.64,
    description: 'Distribution point manager. Operates warehouse network. Secondary leadership tier.',
    attributes: { age: 28, nationality: 'Unknown', priors: 1, threat_score: 71 },
    connections: ['e001', 'e004', 'e009'],
    metadata: { firstSeen: '2026-03-01', lastActive: '2026-04-16', incidentCount: 11 },
  },
  {
    id: 'e003',
    name: 'UNIT 7-ALPHA',
    type: 'LEA',
    confidence: 100,
    centrality: 0.52,
    description: 'Metro PD rapid response. 6-officer unit. Primary surveillance assignment.',
    attributes: { unit_size: 6, agency: 'Metro PD', clearance: 'Priority' },
    connections: ['e001', 'e006'],
    metadata: { firstSeen: '2026-04-01', lastActive: '2026-04-17', incidentCount: 7 },
  },
  {
    id: 'e004',
    name: 'WAREHOUSE DELTA',
    type: 'LOCATION',
    confidence: 85,
    centrality: 0.71,
    description: 'Primary distribution hub. Industrial zone, Sector 4. Monitored 02:00–06:00.',
    attributes: { sector: 4, lat: 40.712, lng: -74.005, risk_score: 88 },
    connections: ['e002', 'e005', 'e007'],
    metadata: { firstSeen: '2026-03-15', lastActive: '2026-04-17', incidentCount: 18 },
  },
  {
    id: 'e005',
    name: 'CASTELLANO IMPORTS LLC',
    type: 'ORGANIZATION',
    confidence: 67,
    centrality: 0.43,
    description: 'Shell company used for logistics cover. Registered in Delaware. No active operations found.',
    attributes: { registered_state: 'Delaware', employees: 3, annual_revenue: '$2.1M' },
    connections: ['e004', 'e002'],
    metadata: { firstSeen: '2026-02-28', lastActive: '2026-04-10', incidentCount: 4 },
  },
  {
    id: 'e006',
    name: 'INFORMANT ECHO-1',
    type: 'WITNESS',
    confidence: 73,
    centrality: 0.31,
    description: 'Protected informant. Inside knowledge of distribution schedule. Identity classified.',
    attributes: { protection_level: 'Alpha', handler: 'UNIT 7-ALPHA' },
    connections: ['e003', 'e001'],
    metadata: { firstSeen: '2026-03-20', lastActive: '2026-04-16', incidentCount: 5 },
  },
];

// ── Mock Report ───────────────────────────────────────────────
export const MOCK_REPORT: IntelReport = {
  id: 'rpt-2831',
  sessionId: 'CS-2831',
  title: 'Financial Fraud Intelligence Report — Shell Corporation Ring',
  generatedAt: '2026-04-17T01:42:00Z',
  confidence: 87,
  threatLevel: 'HIGH',
  executiveSummary: 'Analysis of 1,204 simulated agents across 200 rounds reveals a high-confidence financial fraud operation leveraging 7 shell corporations to launder an estimated $14.3M. The primary nexus is CASTELLANO IMPORTS LLC, with PHANTOM acting as primary architect. Recommended immediate action: financial institution notification and asset freeze.',
  riskMatrix: [
    { id: 'r1', label: 'Money Laundering Expansion',   likelihood: 4, impact: 5, current: true },
    { id: 'r2', label: 'Witness Intimidation',          likelihood: 3, impact: 4, current: false },
    { id: 'r3', label: 'Network Compromise Detection',  likelihood: 2, impact: 5, current: false },
    { id: 'r4', label: 'Asset Seizure Opportunity',     likelihood: 4, impact: 4, current: true },
    { id: 'r5', label: 'Cross-Jurisdiction Conflict',   likelihood: 2, impact: 3, current: false },
  ],
  timeline: [
    { date: '2026-02-14', label: 'Network Established',     type: 'PAST',      confidence: 94, description: 'PHANTOM initiates shell network.' },
    { date: '2026-03-15', label: 'Warehouse Activated',     type: 'PAST',      confidence: 89, description: 'Warehouse Delta begins operations.' },
    { date: '2026-04-17', label: 'Investigation Active',    type: 'PRESENT',   confidence: 100, description: 'Simulation running — agents monitored.' },
    { date: '2026-04-24', label: 'Predicted Escalation',    type: 'PREDICTED', confidence: 78, description: 'Network likely to expand if unchecked.' },
    { date: '2026-05-01', label: 'Critical Window',         type: 'PREDICTED', confidence: 63, description: 'Optimal interdiction window closes.' },
  ],
  keyActors: [
    {
      entityId: 'e001',
      name: 'PHANTOM (Viktor R.)',
      role: 'SUSPECT',
      threatScore: 94,
      bio: 'Primary network coordinator. Sophisticated operational security. Known to switch communication methods every 72 hours.',
      keyActions: ['Established shell network', 'Coordinates financial transfers', 'Manages courier routes'],
      connections: 14,
    },
    {
      entityId: 'e002',
      name: 'WRAITH (Marco L.)',
      role: 'SUSPECT',
      threatScore: 71,
      bio: 'Secondary leadership. Manages physical infrastructure. Vulnerable to surveillance at distribution points.',
      keyActions: ['Operates Warehouse Delta', 'Manages distribution schedule', 'Recruits couriers'],
      connections: 8,
    },
  ],
  recommendedActions: [
    { id: 1, priority: 'IMMEDIATE', title: 'Asset Freeze — Financial Institutions', description: 'Coordinate with 3 identified banks to freeze CASTELLANO IMPORTS LLC accounts pending court order.', assignedTo: 'Financial Crimes Unit', deadline: '2026-04-18' },
    { id: 2, priority: 'HIGH',      title: 'Surveillance — WAREHOUSE DELTA',       description: 'Deploy continuous 24h surveillance. Focus window: 02:00–06:00 local.', assignedTo: 'UNIT 7-ALPHA', deadline: '2026-04-19' },
    { id: 3, priority: 'HIGH',      title: 'Witness Protection — ECHO-1',          description: 'Upgrade protection class to Alpha-1. Relocation assessment required.', assignedTo: 'Witness Protection', deadline: '2026-04-18' },
    { id: 4, priority: 'MEDIUM',    title: 'Inter-Agency Briefing',                description: 'Brief FBI Financial Crimes division on network topology and shell company structure.', assignedTo: 'Case Lead', deadline: '2026-04-20' },
  ],
  confidenceMetadata: { dataQuality: 91, modelCoverage: 84, simulationDepth: 87, evidenceStrength: 79 },
  sections: [
    { id: 's1', title: 'Network Topology Analysis', content: 'The shell corporation network exhibits a hub-and-spoke topology with PHANTOM at center...', confidence: 91 },
    { id: 's2', title: 'Financial Flow Analysis', content: 'Simulated financial flows indicate layering through 7 entities with a total estimated throughput of $14.3M...', confidence: 85 },
  ],
};

// ── Injection Variables ───────────────────────────────────────
export const INJECTION_VARIABLES: InjectionVariable[] = [
  { id: 'patrol_density',  label: 'Patrol Density',   description: 'LEA unit deployment density across sectors', type: 'slider', min: 0, max: 100, step: 5, value: 40, unit: '%' },
  { id: 'witness_active',  label: 'Witness Network',  description: 'Enable/disable active informant reporting', type: 'toggle', value: true },
  { id: 'media_coverage',  label: 'Media Coverage',   description: 'Public awareness level affecting suspect behavior', type: 'slider', min: 0, max: 100, step: 10, value: 30, unit: '%' },
  { id: 'comms_intercept', label: 'Comms Intercept',  description: 'Electronic surveillance coverage', type: 'slider', min: 0, max: 100, step: 5, value: 60, unit: '%' },
  { id: 'threat_level',    label: 'Threat Level',     description: 'Override simulation threat designation', type: 'select', value: 'HIGH', options: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] },
  { id: 'border_control',  label: 'Border Controls',  description: 'Perimeter restriction enforcement', type: 'toggle', value: false },
];

// ── HUD Phase Messages ────────────────────────────────────────
export const HUD_MESSAGES = {
  boot: ['CRIMESCOPE INITIALIZING...', 'THREAT NETWORK SCANNING', 'SYSTEMS ONLINE'],
  scan: ['ENTITY NETWORK: ACTIVE', '2,847 AGENTS PROFILED', 'GRAPH TOPOLOGY: STABLE'],
  convergence: ['CONVERGENCE THRESHOLD MET', 'SIMULATION RUNNING', 'HOTSPOTS IDENTIFIED'],
  report: ['INTELLIGENCE REPORT READY', 'CONFIDENCE: 94%', 'ANALYSIS COMPLETE'],
};

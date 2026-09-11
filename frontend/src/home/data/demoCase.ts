export interface DecompStep {
  id: string
  label: string
  state: 'done' | 'active' | 'queued'
  detail: string
  progress?: { current: number; total: number }
}

export interface DemoEvidenceItem {
  id: string
  filename: string
  kind: 'VID' | 'PDF' | 'IMG'
  sizeLabel: string
  sizeBytes: number
  hash: string
  hashVerified: boolean
  decompSteps: DecompStep[]
}

export interface DemoGraphNode {
  id: string
  label: string
  type: 'person' | 'location' | 'evidence' | 'weapon' | 'event' | 'witness'
  color: string
}

export interface DemoGraphEdge {
  source: string
  target: string
  label: string
  confidence: number
  isHypothetical?: boolean
}

export interface SwarmPersona {
  name: string
  role: string
  mandate: string
  sigil: number
  bias?: string
}

export interface ScenarioEvaluation {
  persona_name: string
  verdict: 'supports' | 'contradicts' | 'inconclusive'
  reasoning: string
  confidence: number
}

export interface DemoScenarioData {
  scenario_id: string
  hypothesis: string
  consensus_verdict: 'mixed' | 'supported' | 'refuted'
  new_entities: DemoGraphNode[]
  new_edges: DemoGraphEdge[]
  evaluations: ScenarioEvaluation[]
}

export const demoEvidenceList: DemoEvidenceItem[] = [
  {
    id: 'ev-01',
    filename: 'evidence_02.mp4',
    kind: 'VID',
    sizeLabel: '1.8 GB',
    sizeBytes: 1800000000,
    hash: 'SHA256: 4f9b8c2e...a10e7b41',
    hashVerified: true,
    decompSteps: [
      { id: 'container', label: 'container', state: 'done', detail: 'container verified' },
      { id: 'metadata', label: 'metadata', state: 'done', detail: 'metadata extracted' },
      { id: 'frames', label: 'frames', state: 'done', detail: '20 keyframes decoded' },
      { id: 'scenes', label: 'scenes', state: 'done', detail: 'scene boundaries indexed' },
      { id: 'objects', label: 'objects', state: 'done', detail: 'weapons and vehicles tagged' },
      { id: 'align', label: 'align', state: 'done', detail: 'temporal sync established' },
    ],
  },
  {
    id: 'ev-02',
    filename: 'witness_report.pdf',
    kind: 'PDF',
    sizeLabel: '18 pp',
    sizeBytes: 2400000,
    hash: 'SHA256: d82c441a...99b4f2c0',
    hashVerified: true,
    decompSteps: [
      { id: 'verify', label: 'verify', state: 'done', detail: 'integrity verified' },
      { id: 'text', label: 'text', state: 'done', detail: '4 text chunks extracted' },
      { id: 'entities', label: 'entities', state: 'done', detail: 'mentions identified' },
      { id: 'events', label: 'events', state: 'done', detail: 'chronology extracted' },
      { id: 'timestamps', label: 'timestamps', state: 'done', detail: 'temporal markers parsed' },
      { id: 'contradictions', label: 'contradictions', state: 'done', detail: 'internal conflict scan' },
    ],
  },
  {
    id: 'ev-03',
    filename: 'street_camera.jpg',
    kind: 'IMG',
    sizeLabel: '820 KB',
    sizeBytes: 820000,
    hash: 'SHA256: e13a5f90...77f0c82d',
    hashVerified: true,
    decompSteps: [
      { id: 'verify', label: 'verify', state: 'done', detail: 'integrity verified' },
      { id: 'thumbnail', label: 'thumbnail', state: 'done', detail: 'multires preview generated' },
      { id: 'ocr', label: 'ocr', state: 'done', detail: 'license plates & signs parsed' },
      { id: 'entities', label: 'entities', state: 'done', detail: 'visual subjects cropped' },
      { id: 'exif', label: 'exif', state: 'done', detail: 'timestamp and GPS anchored' },
    ],
  },
]

export const demoCaseNodes: DemoGraphNode[] = [
  { id: 'n1', label: 'Arthur Pendelton', type: 'person', color: 'oklch(0.60 0.20 20)' },
  { id: 'n2', label: 'Downtown Bank', type: 'location', color: 'oklch(0.75 0.15 70)' },
  { id: 'n3', label: 'Vault Blueprint', type: 'evidence', color: 'oklch(0.65 0.15 250)' },
  { id: 'n4', label: 'Silenced Pistol', type: 'weapon', color: 'oklch(0.65 0.15 250)' },
  { id: 'n5', label: 'Bank Robbery', type: 'event', color: 'oklch(0.65 0.15 250)' },
  { id: 'n6', label: 'Jane Doe', type: 'witness', color: 'oklch(0.60 0.20 20)' },
]

export const demoCaseEdges: DemoGraphEdge[] = [
  { source: 'n1', target: 'n5', label: 'PARTICIPATED_IN', confidence: 0.95 },
  { source: 'n5', target: 'n2', label: 'OCCURRED_AT', confidence: 0.99 },
  { source: 'n1', target: 'n3', label: 'POSSESSED', confidence: 0.45 },
  { source: 'n4', target: 'n5', label: 'USED_IN', confidence: 0.85 },
  { source: 'n6', target: 'n5', label: 'WITNESSED', confidence: 0.92 },
  { source: 'n6', target: 'n1', label: 'IDENTIFIED', confidence: 0.60 },
]

export const demoSwarmPersonas: SwarmPersona[] = [
  {
    name: 'Detective',
    role: 'Lead Investigator',
    mandate: "Finds what doesn't fit.",
    sigil: 1,
  },
  {
    name: 'Defense Attorney',
    role: 'Adversarial Counsel',
    mandate: 'Defends the alternative.',
    sigil: 2,
  },
  {
    name: 'Prosecutor',
    role: 'State Representation',
    mandate: "Argues the state's case.",
    sigil: 3,
  },
  {
    name: 'Forensic Analyst',
    role: 'Physical Evidence Specialist',
    mandate: 'Reads the physical evidence.',
    sigil: 4,
  },
  {
    name: 'Counselor',
    role: 'Victim & Witness Advocate',
    mandate: 'Tracks the human cost.',
    sigil: 5,
  },
]

export const demoScenarioData: DemoScenarioData = {
  scenario_id: 'hyp-72b9a1',
  hypothesis: 'What if Jane assisted Arthur?',
  consensus_verdict: 'mixed',
  new_entities: [
    { id: 'n7', label: 'Offshore Account', type: 'evidence', color: 'oklch(0.65 0.15 250)' },
  ],
  new_edges: [
    { source: 'n1', target: 'n7', label: 'TRANSFERRED_TO', confidence: 0.88, isHypothetical: true },
    { source: 'n6', target: 'n7', label: 'OPENED_ACCOUNT', confidence: 0.75, isHypothetical: true },
  ],
  evaluations: [
    {
      persona_name: 'Jane Doe',
      verdict: 'supports',
      reasoning: 'Jane had bank-system access and a motive; an offshore account fits her teller knowledge of transfer routes.',
      confidence: 0.78,
    },
    {
      persona_name: 'Arthur Pendelton',
      verdict: 'contradicts',
      reasoning: 'Arthur insists he acted alone and has never held a foreign account.',
      confidence: 0.65,
    },
  ],
}

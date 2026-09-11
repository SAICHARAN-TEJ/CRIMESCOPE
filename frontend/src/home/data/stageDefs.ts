export interface StageItem {
  id: string
  label: string
  glyph: string
  tagline: string
  state: 'COMPLETED' | 'ACTIVE' | 'QUEUED' | 'WAITING' | 'SKIPPED'
  itemCount: number | null
  detail: string
  agents: string[]
  honestNote?: string
  checklist?: Array<{ label: string; done: boolean; inProgress?: boolean }>
  findingLines?: string[]
}

export const pipelineStages: StageItem[] = [
  {
    id: 'ingest',
    label: 'Ingest',
    glyph: '✓',
    tagline: 'Secure multi-modal evidence registration.',
    state: 'COMPLETED',
    itemCount: 3,
    detail: '3 evidence items received',
    agents: ['video', 'document', 'image'],
  },
  {
    id: 'triage',
    label: 'Triage',
    glyph: '✓',
    tagline: 'Modality routing & resource allocation.',
    state: 'COMPLETED',
    itemCount: 3,
    detail: 'routing evidence by modality',
    agents: ['video', 'document', 'image'],
  },
  {
    id: 'extract',
    label: 'Extract',
    glyph: '✓',
    tagline: 'Decomposition across parallel worker pools.',
    state: 'COMPLETED',
    itemCount: 3,
    detail: 'video and document extraction workers running',
    agents: ['video', 'document'],
    checklist: [
      { label: 'container', done: true },
      { label: 'metadata', done: true },
      { label: 'frames', done: false, inProgress: true },
    ],
  },
  {
    id: 'understand',
    label: 'Understand',
    glyph: '✓',
    tagline: 'Quorum NER and relationship extraction.',
    state: 'COMPLETED',
    itemCount: 13,
    detail: '13 entities, 22 relationships',
    agents: ['entity', 'consensus'],
    honestNote: '3 entity agents vote, consensus reconciles (quorum NER, not one model\'s guess).',
  },
  {
    id: 'connect',
    label: 'Connect',
    glyph: '✓',
    tagline: 'Graph persistence with transactional buffering.',
    state: 'COMPLETED',
    itemCount: 13,
    detail: 'writing entities and relationships to graph',
    agents: ['graph'],
    honestNote: 'Neo4j, buffered writes, DLQ on failure.',
  },
  {
    id: 'challenge',
    label: 'Challenge',
    glyph: '✓',
    tagline: 'Adversarial peer review across persona swarm.',
    state: 'COMPLETED',
    itemCount: 2,
    detail: '2 perspectives reviewing the graph',
    agents: ['persona'],
    honestNote: 'persona debate',
  },
  {
    id: 'verify',
    label: 'Verify',
    glyph: '·',
    tagline: 'Automated ground truth and falsification pass.',
    state: 'SKIPPED',
    itemCount: null,
    detail: 'verification pass arrives in Phase 5',
    agents: [],
    honestNote: 'CrimeScope shows you what the pipeline actually did. Nothing is faked.',
  },
  {
    id: 'report',
    label: 'Report',
    glyph: '✓',
    tagline: 'Evidence-linked forensic findings summary.',
    state: 'COMPLETED',
    itemCount: 13,
    detail: 'assembling pipeline result',
    agents: ['report'],
    findingLines: [
      'Finding 01: Vault timing correlates with shift change logs.',
      'Finding 02: P-018 registered at perimeter 3 minutes prior.',
      'Finding 03: POSSESSED relationship confidence remains low (0.45).',
    ],
  },
]

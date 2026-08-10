// DEMO FIXTURE — do not import outside src/demo
import type { GraphNode, GraphEdge } from '@/types'

export const demoNodes: GraphNode[] = [
  { id: 'n1', label: 'Arthur Pendelton', type: 'person', properties: {} },
  { id: 'n2', label: 'Downtown Bank', type: 'location', properties: {} },
  { id: 'n3', label: 'Vault Blueprint', type: 'evidence', properties: {} },
  { id: 'n4', label: 'Silenced Pistol', type: 'weapon', properties: {} },
  { id: 'n5', label: 'Bank Robbery', type: 'event', properties: {} },
  { id: 'n6', label: 'Jane Doe', type: 'witness', properties: {} },
]

export const demoEdges: GraphEdge[] = [
  { source: 'n1', target: 'n5', label: 'PARTICIPATED_IN', properties: { confidence: 0.95 } },
  { source: 'n5', target: 'n2', label: 'OCCURRED_AT', properties: { confidence: 0.99 } },
  { source: 'n1', target: 'n3', label: 'POSSESSED', properties: { confidence: 0.45 } },
  { source: 'n4', target: 'n5', label: 'USED_IN', properties: { confidence: 0.85 } },
  { source: 'n6', target: 'n5', label: 'WITNESSED', properties: { confidence: 0.92 } },
  { source: 'n6', target: 'n1', label: 'IDENTIFIED', properties: { confidence: 0.60 } },
]

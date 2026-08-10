// DEMO FIXTURE — do not import outside src/demo
import type { ScenarioDiff } from '@/types'

export const demoScenarioDiff: ScenarioDiff = {
  scenario_id: 'hyp-72b9a1',
  nodes_added: [
    { id: 'n7', label: 'Offshore Account', type: 'evidence', properties: {} }
  ],
  edges_added: [
    { source: 'n1', target: 'n7', label: 'TRANSFERRED_TO', properties: { confidence: 0.88, isHypothetical: true } },
    { source: 'n6', target: 'n7', label: 'OPENED_ACCOUNT', properties: { confidence: 0.75, isHypothetical: true } }
  ],
  insights: [
    'If Jane Doe assisted Arthur, the stolen funds likely bypassed traditional laundering and moved directly to an offshore account she opened.',
    'This hypothesis introduces an "Offshore Account" node linking both individuals, suggesting premeditated collusion.'
  ]
}

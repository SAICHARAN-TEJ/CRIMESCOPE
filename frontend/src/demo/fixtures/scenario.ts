// DEMO FIXTURE — do not import outside src/demo
// §14 final vocabulary: new_entities / new_edges / evaluations / consensus_verdict.
import type { ScenarioDiff } from '@/types'

export const demoScenarioDiff: ScenarioDiff = {
  scenario_id: 'hyp-72b9a1',
  consensus_verdict: 'mixed',
  new_entities: [
    { id: 'n7', label: 'Offshore Account', type: 'evidence', properties: {} }
  ],
  new_edges: [
    { source: 'n1', target: 'n7', label: 'TRANSFERRED_TO', properties: { confidence: 0.88, isHypothetical: true } },
    { source: 'n6', target: 'n7', label: 'OPENED_ACCOUNT', properties: { confidence: 0.75, isHypothetical: true } }
  ],
  evaluations: [
    {
      persona_name: 'Jane Doe',
      verdict: 'supports',
      reasoning: 'Jane had bank-system access and a motive; an offshore account fits her teller knowledge of transfer routes.',
      confidence: 0.78
    },
    {
      persona_name: 'Arthur Pendelton',
      verdict: 'contradicts',
      reasoning: 'Arthur insists he acted alone and has never held a foreign account.',
      confidence: 0.65
    }
  ],
  // Derived client-side by the store when the SCENARIO_DIFF event is replayed;
  // kept here for reference/parity with the derived shape.
  insights: [
    'If Jane Doe assisted Arthur, the stolen funds likely bypassed traditional laundering and moved directly to an offshore account she opened.',
    'This hypothesis introduces an "Offshore Account" node linking both individuals, suggesting premeditated collusion.'
  ]
}

// DEMO FIXTURE — do not import outside src/demo
import type { PersonaProfile, PersonaInsight } from '@/types'

export const demoPersonas: PersonaProfile[] = [
  {
    id: 'p1',
    name: 'Jane Doe',
    role: 'Witness / Former Teller',
    motivation: 'Wants to protect her family but holds resentment towards the bank.',
    background: 'Worked at Downtown Bank for 5 years. Fired under suspicious circumstances two weeks prior to the robbery.',
    bias: 'Highly distrustful of bank management, likely to exaggerate their incompetence.'
  },
  {
    id: 'p2',
    name: 'Arthur Pendelton',
    role: 'Primary Suspect',
    motivation: 'Needs money to pay off underground gambling debts.',
    background: 'Former security contractor with extensive knowledge of vault systems. Recently seen heavily in debt.',
    bias: 'Defensive, deflects blame onto internal bank employees.'
  }
]

export const demoInsights: PersonaInsight[] = [
  {
    persona_id: 'p1',
    persona_name: 'Jane Doe',
    insight: 'Arthur\'s knowledge of the vault timing aligns with the security shift changes she remembers.',
    confidence: 0.85,
    nodes_referenced: ['n1', 'n2', 'n6']
  },
  {
    persona_id: 'p2',
    persona_name: 'Arthur Pendelton',
    insight: 'The blueprints were allegedly given to him by an insider, potentially implicating Jane.',
    confidence: 0.75,
    nodes_referenced: ['n1', 'n3', 'n6']
  }
]

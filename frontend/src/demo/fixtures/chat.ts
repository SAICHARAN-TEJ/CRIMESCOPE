// DEMO FIXTURE — do not import outside src/demo
import type { ChatMessage } from '@/types'

export const demoChatSequence: ChatMessage[] = [
  { role: 'user', content: 'What is the connection between Arthur and Jane?' },
  { role: 'agent', content: 'Based on the extracted entities and the knowledge graph, Arthur Pendelton and Jane Doe are both linked to the Downtown Bank incident. Jane was recently terminated from the bank, and Arthur acquired a vault blueprint. The confidence of their direct collaboration is low (0.45), but Jane\'s timeline overlaps with Arthur\'s reconnaissance phase.' },
  { role: 'user', content: 'Did Arthur use the silenced pistol during the robbery?' },
  { role: 'agent', content: 'The graph indicates the silenced pistol was USED_IN the Bank Robbery event with high confidence (0.85). Arthur Pendelton is linked to the robbery (0.95), suggesting he was likely the one wielding it.' },
]

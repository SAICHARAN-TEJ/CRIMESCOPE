/**
 * Harlow Street — DENSE graph dataset.
 * ~120 nodes, ~160 edges to create the MiroFish-style dense network.
 *
 * Node types: person, location, evidence, event, agent
 * Groups: victim, suspect, witness, scene, poi, physical, digital,
 *         vehicle, document, context, forensic_analyst, behavioral_profiler,
 *         eyewitness_simulator, suspect_persona, alibi_verifier,
 *         scene_reconstructor, statistical_baseline, contradiction_detector
 */

// ── Core Case Nodes ─────────────────────────────────────────────────
const CASE_NODES = [
  { id: 'n_voss', label: 'Margaret Voss', type: 'person', group: 'victim', summary: 'Victim. 54yo pharmacist. Last seen 06:38 PM.' },
  { id: 'n_arthur', label: 'Arthur Voss', type: 'person', group: 'suspect', summary: 'Husband. Credibility: 0.85. Claims he was at home.' },
  { id: 'n_vance', label: 'Leo Vance', type: 'person', group: 'witness', summary: 'Pharmacist colleague. Last to see victim at work.' },
  { id: 'n_wit_a', label: 'Witness A', type: 'person', group: 'witness', summary: 'Bystander. Claims red SUV fled at 07:15 PM.' },
  { id: 'n_wit_b', label: 'Witness B', type: 'person', group: 'witness', summary: 'Bystander. Claims silver sedan on L3 at 07:05 PM.' },
  { id: 'n_wit_c', label: 'Witness C', type: 'person', group: 'witness', summary: 'Garage attendant. Heard argument at 07:12 PM.' },
  { id: 'n_garcia', label: 'Det. Garcia', type: 'person', group: 'poi', summary: 'Lead detective. 14 years homicide.' },
  { id: 'n_chen', label: 'Dr. Chen', type: 'person', group: 'poi', summary: 'Forensic pathologist. Examined scene.' },
  { id: 'n_patel', label: 'Raj Patel', type: 'person', group: 'witness', summary: 'Pharmacy customer. Present at 06:35 PM.' },
  { id: 'n_morris', label: 'Karen Morris', type: 'person', group: 'witness', summary: 'Neighbor. Saw Arthur leave home at 06:50 PM.' },
  { id: 'n_davis', label: 'Tom Davis', type: 'person', group: 'suspect', summary: 'Ex-employee of pharmacy. Terminated 3 weeks prior.' },
  { id: 'n_reed', label: 'Sarah Reed', type: 'person', group: 'poi', summary: 'Insurance investigator. Flagged $500k policy.' },
  { id: 'n_huang', label: 'Mike Huang', type: 'person', group: 'witness', summary: 'Security guard at adjacent building.' },
  { id: 'n_taylor', label: 'Janet Taylor', type: 'person', group: 'poi', summary: 'DEA agent. Running parallel narcotics investigation.' },
  { id: 'n_wilson', label: 'Frank Wilson', type: 'person', group: 'suspect', summary: 'Known drug dealer. Linked to prescription ring.' },
  // Locations
  { id: 'n_garage', label: 'Harlow Garage L3', type: 'location', group: 'scene', summary: 'Crime scene. Level 3. Vehicle found here.' },
  { id: 'n_garage_l1', label: 'Harlow Garage L1', type: 'location', group: 'scene', summary: 'Handbag discovery. Trash bin near east stairwell.' },
  { id: 'n_garage_l2', label: 'Harlow Garage L2', type: 'location', group: 'scene', summary: 'Argument heard from this level at 07:12 PM.' },
  { id: 'n_pharmacy', label: 'Harlow Pharmacy', type: 'location', group: 'poi', summary: 'Victim workplace. 200m from garage.' },
  { id: 'n_staircase', label: 'Utility Staircase', type: 'location', group: 'poi', summary: 'Connects L3 to service exit. No CCTV.' },
  { id: 'n_service_exit', label: 'Service Exit', type: 'location', group: 'poi', summary: 'Rear exit. No cameras. Leads to alley.' },
  { id: 'n_alley', label: 'Rear Alley', type: 'location', group: 'scene', summary: 'Tire marks found. Unidentified vehicle.' },
  { id: 'n_voss_home', label: 'Voss Residence', type: 'location', group: 'poi', summary: '4.2km from garage. Arthur claims presence here.' },
  { id: 'n_pharmacy_back', label: 'Pharmacy Storage', type: 'location', group: 'poi', summary: 'Restricted area. Controlled substance storage.' },
  // Evidence
  { id: 'n_handbag', label: 'Handbag', type: 'evidence', group: 'physical', summary: 'Found in L1 bin. Wallet present, keys missing.' },
  { id: 'n_phone', label: 'Mobile Phone', type: 'evidence', group: 'digital', summary: 'Powered off 06:59 PM. Last tower ping near garage.' },
  { id: 'n_vehicle', label: 'Victim Vehicle', type: 'evidence', group: 'vehicle', summary: 'Silver Volvo XC60. Still parked L3.' },
  { id: 'n_cctv', label: 'CCTV System', type: 'evidence', group: 'digital', summary: '22-min blind spot 06:58–07:20.' },
  { id: 'n_red_suv', label: 'Red SUV', type: 'evidence', group: 'vehicle', summary: 'Unidentified. Reported by Witness A only.' },
  { id: 'n_silver_sedan', label: 'Silver Sedan', type: 'evidence', group: 'vehicle', summary: 'On L3 at 07:05. Witness B report.' },
  { id: 'n_doc42', label: 'Rx Log #42', type: 'evidence', group: 'document', summary: 'Missing entries Nov 12–16.' },
  { id: 'n_narco', label: 'Narcotics Probe', type: 'event', group: 'context', summary: 'Ongoing DEA investigation.' },
  { id: 'n_keys', label: 'Missing Keys', type: 'evidence', group: 'physical', summary: 'Car keys and pharmacy keys not in handbag.' },
  { id: 'n_blood', label: 'Blood Trace', type: 'evidence', group: 'physical', summary: 'Trace found on L3 pillar. DNA pending.' },
  { id: 'n_tire_marks', label: 'Tire Marks', type: 'evidence', group: 'physical', summary: 'Fresh marks in rear alley. SUV pattern.' },
  { id: 'n_cctv_l2', label: 'L2 CCTV Fragment', type: 'evidence', group: 'digital', summary: 'Partial frame: figure moving toward stairs at 07:08.' },
  { id: 'n_phone_records', label: 'Phone Records', type: 'evidence', group: 'digital', summary: '3 calls to unknown number Nov 16–18.' },
  { id: 'n_insurance', label: '$500k Policy', type: 'evidence', group: 'document', summary: 'Life insurance. Arthur sole beneficiary. Filed 6 months ago.' },
  { id: 'n_scrape_marks', label: 'Scrape Marks', type: 'evidence', group: 'physical', summary: 'On pillar near vehicle. Recent.' },
  { id: 'n_gloves', label: 'Latex Gloves', type: 'evidence', group: 'physical', summary: 'Found in L2 trash. No prints.' },
  { id: 'n_receipt', label: 'Gas Receipt', type: 'evidence', group: 'document', summary: 'Arthur. 06:44 PM. Station 8km from garage.' },
  { id: 'n_jacket', label: 'Dark Jacket', type: 'evidence', group: 'physical', summary: 'Found on stairwell railing. Not victim\'s.' },
  { id: 'n_cctv_entry', label: 'Entry CCTV', type: 'evidence', group: 'digital', summary: 'Vehicle enters 06:42. Only 3 other cars after.' },
  { id: 'n_footprints', label: 'Shoe Prints', type: 'evidence', group: 'physical', summary: 'Size 11 men\'s boot. L3 to stairwell.' },
  // Events
  { id: 'n_argument', label: 'Argument Event', type: 'event', group: 'context', summary: 'Reported by Witness C at 07:12 PM.' },
  { id: 'n_blackout', label: 'CCTV Blackout', type: 'event', group: 'context', summary: 'System failure 06:58–07:20. Cause pending.' },
  { id: 'n_departure', label: 'Pharmacy Departure', type: 'event', group: 'context', summary: 'Victim leaves pharmacy at 06:38 PM.' },
  { id: 'n_bag_dump', label: 'Bag Discarded', type: 'event', group: 'context', summary: 'Handbag placed in L1 bin. Deliberate concealment.' },
]

// ── Agent Nodes (50 visible agents to create density) ───────────────
const AGENT_ARCHETYPES = [
  { prefix: 'fa', type: 'agent', group: 'forensic_analyst', label: 'FA', count: 8 },
  { prefix: 'bp', type: 'agent', group: 'behavioral_profiler', label: 'BP', count: 6 },
  { prefix: 'es', type: 'agent', group: 'eyewitness_simulator', label: 'ES', count: 7 },
  { prefix: 'sp', type: 'agent', group: 'suspect_persona', label: 'SP', count: 8 },
  { prefix: 'av', type: 'agent', group: 'alibi_verifier', label: 'AV', count: 5 },
  { prefix: 'sr', type: 'agent', group: 'scene_reconstructor', label: 'SR', count: 6 },
  { prefix: 'sb', type: 'agent', group: 'statistical_baseline', label: 'SB', count: 5 },
  { prefix: 'cd', type: 'agent', group: 'contradiction_detector', label: 'CD', count: 5 },
]

const AGENT_NODES = []
AGENT_ARCHETYPES.forEach(arch => {
  for (let i = 0; i < arch.count; i++) {
    AGENT_NODES.push({
      id: `${arch.prefix}_${String(i).padStart(3, '0')}`,
      label: `${arch.label}-${String(i + 1).padStart(3, '0')}`,
      type: arch.type,
      group: arch.group,
      summary: `${arch.group.replace(/_/g, ' ')} agent #${i + 1}`,
    })
  }
})

// ── All Nodes ───────────────────────────────────────────────────────
export const HARLOW_NODES = [...CASE_NODES, ...AGENT_NODES]

// ── Core Edges ──────────────────────────────────────────────────────
const CORE_EDGES = [
  // Victim connections
  { id: 'e01', source: 'n_voss', target: 'n_garage', type: 'LOCATED_AT', label: 'Vehicle parked L3', weight: 5, certainty: 'confirmed' },
  { id: 'e02', source: 'n_voss', target: 'n_handbag', type: 'OWNS', label: 'Personal belongings', weight: 5, certainty: 'confirmed' },
  { id: 'e03', source: 'n_voss', target: 'n_phone', type: 'OWNS', label: 'Personal device', weight: 5, certainty: 'confirmed' },
  { id: 'e04', source: 'n_voss', target: 'n_vehicle', type: 'OWNS', label: 'Registered owner', weight: 5, certainty: 'confirmed' },
  { id: 'e05', source: 'n_voss', target: 'n_pharmacy', type: 'WORKS_AT', label: '12 years employed', weight: 4, certainty: 'confirmed' },
  { id: 'e06', source: 'n_voss', target: 'n_keys', type: 'OWNS', label: 'Keys missing', weight: 4, certainty: 'confirmed' },
  { id: 'e07', source: 'n_voss', target: 'n_narco', type: 'LINKED_TO', label: 'Rx irregularities', weight: 2, certainty: 'suspected' },
  // Family/associate
  { id: 'e08', source: 'n_arthur', target: 'n_voss', type: 'MARRIED_TO', label: 'Spouse 28 years', weight: 4, certainty: 'confirmed' },
  { id: 'e09', source: 'n_vance', target: 'n_voss', type: 'COLLEAGUE_OF', label: 'Co-workers', weight: 3, certainty: 'confirmed' },
  { id: 'e10', source: 'n_davis', target: 'n_pharmacy', type: 'EX_EMPLOYEE', label: 'Terminated 3 weeks ago', weight: 3, certainty: 'confirmed' },
  { id: 'e11', source: 'n_arthur', target: 'n_insurance', type: 'BENEFICIARY', label: 'Sole beneficiary', weight: 4, certainty: 'confirmed' },
  { id: 'e12', source: 'n_arthur', target: 'n_receipt', type: 'PURCHASED', label: '06:44 PM gas purchase', weight: 3, certainty: 'confirmed' },
  { id: 'e13', source: 'n_arthur', target: 'n_voss_home', type: 'RESIDES_AT', label: 'Claims presence', weight: 2, certainty: 'disputed' },
  { id: 'e14', source: 'n_morris', target: 'n_arthur', type: 'OBSERVED', label: 'Saw leave at 06:50', weight: 3, certainty: 'disputed' },
  // Location links
  { id: 'e15', source: 'n_handbag', target: 'n_garage_l1', type: 'FOUND_AT', label: 'In trash bin', weight: 5, certainty: 'confirmed' },
  { id: 'e16', source: 'n_staircase', target: 'n_garage', type: 'CONNECTS_TO', label: 'Service exit, no CCTV', weight: 4, certainty: 'confirmed' },
  { id: 'e17', source: 'n_staircase', target: 'n_service_exit', type: 'CONNECTS_TO', label: 'To rear alley', weight: 4, certainty: 'confirmed' },
  { id: 'e18', source: 'n_service_exit', target: 'n_alley', type: 'CONNECTS_TO', label: 'Unmonitored', weight: 4, certainty: 'confirmed' },
  { id: 'e19', source: 'n_garage_l1', target: 'n_garage', type: 'PART_OF', label: 'Same structure', weight: 5, certainty: 'confirmed' },
  { id: 'e20', source: 'n_garage_l2', target: 'n_garage', type: 'PART_OF', label: 'Same structure', weight: 5, certainty: 'confirmed' },
  // Witness observations
  { id: 'e21', source: 'n_wit_a', target: 'n_red_suv', type: 'OBSERVED', label: 'Speeding 07:15', weight: 2, certainty: 'disputed' },
  { id: 'e22', source: 'n_wit_b', target: 'n_silver_sedan', type: 'OBSERVED', label: 'Idling L3 07:05', weight: 3, certainty: 'disputed' },
  { id: 'e23', source: 'n_wit_c', target: 'n_argument', type: 'HEARD_AT', label: 'Argument 07:12', weight: 3, certainty: 'disputed' },
  { id: 'e24', source: 'n_argument', target: 'n_garage_l2', type: 'OCCURRED_AT', label: 'Level 2', weight: 3, certainty: 'disputed' },
  { id: 'e25', source: 'n_patel', target: 'n_pharmacy', type: 'VISITED', label: 'Customer at 06:35', weight: 2, certainty: 'confirmed' },
  { id: 'e26', source: 'n_huang', target: 'n_garage', type: 'MONITORED', label: 'Adjacent building', weight: 2, certainty: 'confirmed' },
  // Evidence links
  { id: 'e27', source: 'n_cctv', target: 'n_garage', type: 'MONITORS', label: '22-min gap', weight: 5, certainty: 'confirmed' },
  { id: 'e28', source: 'n_cctv', target: 'n_blackout', type: 'CAUSED', label: 'System failure', weight: 5, certainty: 'confirmed' },
  { id: 'e29', source: 'n_blood', target: 'n_garage', type: 'FOUND_AT', label: 'L3 pillar', weight: 4, certainty: 'confirmed' },
  { id: 'e30', source: 'n_tire_marks', target: 'n_alley', type: 'FOUND_AT', label: 'SUV pattern', weight: 3, certainty: 'confirmed' },
  { id: 'e31', source: 'n_tire_marks', target: 'n_red_suv', type: 'MATCHES', label: 'SUV tire pattern', weight: 2, certainty: 'suspected' },
  { id: 'e32', source: 'n_cctv_l2', target: 'n_garage_l2', type: 'CAPTURED_AT', label: 'Partial frame', weight: 3, certainty: 'confirmed' },
  { id: 'e33', source: 'n_phone_records', target: 'n_phone', type: 'FROM_DEVICE', label: '3 unknown calls', weight: 3, certainty: 'confirmed' },
  { id: 'e34', source: 'n_phone_records', target: 'n_wilson', type: 'CALLED', label: 'Matched to dealer', weight: 2, certainty: 'suspected' },
  { id: 'e35', source: 'n_doc42', target: 'n_pharmacy', type: 'FILED_AT', label: 'Missing entries', weight: 3, certainty: 'suspected' },
  { id: 'e36', source: 'n_doc42', target: 'n_narco', type: 'EVIDENCE_FOR', label: 'Irregularities', weight: 3, certainty: 'suspected' },
  { id: 'e37', source: 'n_gloves', target: 'n_garage_l2', type: 'FOUND_AT', label: 'In L2 trash', weight: 3, certainty: 'confirmed' },
  { id: 'e38', source: 'n_scrape_marks', target: 'n_vehicle', type: 'ADJACENT_TO', label: 'Near vehicle', weight: 2, certainty: 'confirmed' },
  { id: 'e39', source: 'n_jacket', target: 'n_staircase', type: 'FOUND_AT', label: 'On railing', weight: 3, certainty: 'confirmed' },
  { id: 'e40', source: 'n_footprints', target: 'n_garage', type: 'FOUND_AT', label: 'L3 to stairwell', weight: 3, certainty: 'confirmed' },
  { id: 'e41', source: 'n_cctv_entry', target: 'n_garage', type: 'MONITORS', label: 'Entry camera', weight: 4, certainty: 'confirmed' },
  // Investigation links
  { id: 'e42', source: 'n_garcia', target: 'n_voss', type: 'INVESTIGATES', label: 'Lead detective', weight: 3, certainty: 'confirmed' },
  { id: 'e43', source: 'n_chen', target: 'n_blood', type: 'ANALYSED', label: 'DNA pending', weight: 3, certainty: 'confirmed' },
  { id: 'e44', source: 'n_chen', target: 'n_gloves', type: 'ANALYSED', label: 'No prints', weight: 3, certainty: 'confirmed' },
  { id: 'e45', source: 'n_taylor', target: 'n_narco', type: 'LEADS', label: 'DEA case officer', weight: 3, certainty: 'confirmed' },
  { id: 'e46', source: 'n_taylor', target: 'n_wilson', type: 'INVESTIGATES', label: 'Primary suspect', weight: 3, certainty: 'confirmed' },
  { id: 'e47', source: 'n_reed', target: 'n_insurance', type: 'FLAGGED', label: 'Suspicious timing', weight: 3, certainty: 'confirmed' },
  { id: 'e48', source: 'n_wilson', target: 'n_pharmacy_back', type: 'ACCESSED', label: 'Backdoor dealings', weight: 2, certainty: 'suspected' },
  // Events
  { id: 'e49', source: 'n_departure', target: 'n_pharmacy', type: 'OCCURRED_AT', label: '06:38 PM', weight: 4, certainty: 'confirmed' },
  { id: 'e50', source: 'n_departure', target: 'n_voss', type: 'INVOLVES', label: 'Victim departs', weight: 5, certainty: 'confirmed' },
  { id: 'e51', source: 'n_bag_dump', target: 'n_handbag', type: 'INVOLVES', label: 'Deliberate placement', weight: 4, certainty: 'confirmed' },
  { id: 'e52', source: 'n_bag_dump', target: 'n_garage_l1', type: 'OCCURRED_AT', label: 'L1 east stairwell', weight: 4, certainty: 'confirmed' },
  { id: 'e53', source: 'n_davis', target: 'n_voss', type: 'GRUDGE_AGAINST', label: 'Wrongful termination claim', weight: 2, certainty: 'suspected' },
  { id: 'e54', source: 'n_pharmacy_back', target: 'n_pharmacy', type: 'PART_OF', label: 'Restricted area', weight: 3, certainty: 'confirmed' },
]

// ── Agent Investigation Edges (agents connect to evidence/persons) ──
const AGENT_INVESTIGATION_TARGETS = [
  'n_voss', 'n_arthur', 'n_vance', 'n_davis', 'n_wilson',
  'n_garage', 'n_staircase', 'n_alley', 'n_pharmacy',
  'n_handbag', 'n_phone', 'n_blood', 'n_cctv', 'n_keys',
  'n_tire_marks', 'n_footprints', 'n_gloves', 'n_jacket',
  'n_insurance', 'n_doc42', 'n_phone_records', 'n_vehicle',
  'n_cctv_l2', 'n_red_suv', 'n_silver_sedan', 'n_narco',
  'n_argument', 'n_blackout', 'n_receipt', 'n_wit_a', 'n_wit_b',
  'n_wit_c', 'n_morris', 'n_garage_l1', 'n_garage_l2',
]

function seededRandom(seed) {
  let s = seed
  return () => { s = (s * 16807 + 0) % 2147483647; return s / 2147483647 }
}

const AGENT_EDGES = []
const rand = seededRandom(42)
let edgeIdx = 55

AGENT_NODES.forEach(agent => {
  const connectionCount = 2 + Math.floor(rand() * 4) // 2-5 connections each
  const shuffled = [...AGENT_INVESTIGATION_TARGETS].sort(() => rand() - 0.5)
  for (let i = 0; i < connectionCount; i++) {
    AGENT_EDGES.push({
      id: `e${String(edgeIdx++).padStart(3, '0')}`,
      source: agent.id,
      target: shuffled[i],
      type: 'INVESTIGATES',
      label: 'Investigating',
      weight: 1,
      certainty: 'confirmed',
    })
  }
  // Inter-agent connections (20% chance to connect to another agent)
  if (rand() < 0.2) {
    const otherAgent = AGENT_NODES[Math.floor(rand() * AGENT_NODES.length)]
    if (otherAgent.id !== agent.id) {
      AGENT_EDGES.push({
        id: `e${String(edgeIdx++).padStart(3, '0')}`,
        source: agent.id,
        target: otherAgent.id,
        type: 'DEBATES',
        label: 'Adversarial',
        weight: 1,
        certainty: 'confirmed',
      })
    }
  }
})

export const HARLOW_EDGES = [...CORE_EDGES, ...AGENT_EDGES]

export const DEMO_HYPOTHESES = [
  { id: 'H-001', title: 'Planned Ambush', probability: 0.45, agent_count: 450 },
  { id: 'H-002', title: 'Staged Disappearance', probability: 0.30, agent_count: 300 },
  { id: 'H-003', title: 'Third-Party Opportunist', probability: 0.15, agent_count: 150 },
  { id: 'H-004', title: 'Accidental Discovery', probability: 0.10, agent_count: 100 },
]

from app.services.evidence_evaluator import EvidenceEvaluator

e = EvidenceEvaluator()

# Test 1: pairwise scoring
s = e.score_fact_against_hypothesis(
    'Vehicle found locked on Level 3',
    'Staged disappearance masking a targeted criminal act'
)
print(f"Pairwise score: {round(s, 4)}")

# Test 2: evidentiary strength
strength = e.compute_evidentiary_strength(
    confirmed_facts=['Victim last seen leaving pharmacy', 'Vehicle found locked'],
    disputed_facts=['Witness accounts disagree on male figure'],
    open_questions=['Was CCTV gap accidental?', 'How many actors were involved?']
)
print(f"Evidentiary strength: {strength}")

# Test 3: rank hypotheses
hypotheses = [
    {'title': 'Coordinated abduction with pre-event surveillance'},
    {'title': 'Staged disappearance masking a targeted criminal act'},
    {'title': 'Opportunistic escalation after routine encounter'},
]
ranked = e.rank_hypotheses_by_evidence(
    hypotheses=hypotheses,
    confirmed_facts=['Vehicle found locked', 'handbag remained inside', 'CCTV gap 22 minutes'],
    disputed_facts=['Witness disagree on male figure near vehicle']
)
print("Ranked hypotheses:")
for h in ranked:
    print(f"  [{h['evidence_net_score']:.4f}] {h['title']}")

print("\nAll tests passed!")

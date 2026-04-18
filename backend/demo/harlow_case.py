# SPDX-License-Identifier: AGPL-3.0-only
"""
Harlow Street — benchmark case for demo mode.

Contains the seed packet (fed to agents) and a pre-built
graph dataset (fed to the frontend D3 visualiser).
"""

HARLOW_SEED = {
    "case_id": "harlow-001",
    "title": "Harlow St Parking Garage Disappearance",
    "victim": "Margaret Voss, 54, Pharmacist",
    "location": "Harlow Street Parking Garage, Level 3",
    "incident_time": "2024-11-18, approx 07:10 PM",
    "confirmed_facts": [
        "Victim vehicle entered garage at 06:42 PM.",
        "Victim last seen on CCTV leaving pharmacy at 06:38 PM.",
        "Phone powered off at 06:59 PM.",
        "Handbag found in bin on Level 1 at 07:45 PM.",
        "Garage attendant reports no unauthorised vehicles left via main exit.",
    ],
    "disputed_facts": [
        "Witness A claims a red SUV sped away at 07:15 PM.",
        "Witness B claims a silver sedan was idling on L3 at 07:05 PM.",
        "Witness C reports hearing an argument at 07:12 PM from L2.",
        "Pharmacist colleague claims Margaret seemed 'extremely anxious' before leaving.",
    ],
    "key_persons": [
        {"name": "Arthur Voss", "role": "Husband", "credibility": 0.85},
        {"name": "Leo Vance", "role": "Pharmacist Colleague", "credibility": 0.92},
        {"name": "Witness A", "role": "Bystander", "credibility": 0.45},
        {"name": "Witness B", "role": "Bystander", "credibility": 0.60},
        {"name": "Witness C", "role": "Garage Attendant", "credibility": 0.88},
    ],
    "timeline_constraints": {
        "06:58 PM": "CCTV blind spot begins",
        "07:20 PM": "CCTV monitoring resumes; victim vehicle still parked",
    },
    "open_questions": [
        "Where was the phone between 06:42 and 06:59?",
        "Why was the handbag on Level 1 if the vehicle is on Level 3?",
        "Is there an alternative exit used by the 'red SUV'?",
        "What was the content of the 'anxious' phone call Leo Vance mentions?",
        "Was the CCTV gap deliberate tampering or a system fault?",
        "Who has access to the utility staircase near L3?",
        "What is the connection between Margaret and the local narcotics investigation?",
        "Is Document #42 (prescription log) missing entries?",
        "Why was the phone powered off specifically at 06:59?",
        "What was found in the tire treads of the silver sedan?",
    ],
    "directive": (
        "Reconstruct the 22-minute window (06:58–07:20). "
        "Focus on the discrepancy between vehicle position and handbag discovery."
    ),
}

# ── Pre-built graph for the frontend demo ────────────────────────────────

HARLOW_NODES = [
    {"id": "n_voss", "label": "Margaret Voss", "type": "person", "group": "victim",
     "summary": "Victim. 54yo pharmacist. Last seen 06:38 PM."},
    {"id": "n_arthur", "label": "Arthur Voss", "type": "person", "group": "suspect",
     "summary": "Husband. Credibility: 0.85. Claims he was at home."},
    {"id": "n_vance", "label": "Leo Vance", "type": "person", "group": "witness",
     "summary": "Pharmacist colleague. Last person to see victim at work."},
    {"id": "n_wit_a", "label": "Witness A", "type": "person", "group": "witness",
     "summary": "Bystander. Claims red SUV fled at 07:15 PM. Low credibility."},
    {"id": "n_wit_b", "label": "Witness B", "type": "person", "group": "witness",
     "summary": "Bystander. Claims silver sedan on L3 at 07:05 PM."},
    {"id": "n_wit_c", "label": "Witness C", "type": "person", "group": "witness",
     "summary": "Garage attendant. Heard argument at 07:12 PM from L2."},
    {"id": "n_garage", "label": "Harlow Garage L3", "type": "location", "group": "scene",
     "summary": "Crime scene. Level 3. Vehicle found here."},
    {"id": "n_garage_l1", "label": "Harlow Garage L1", "type": "location", "group": "scene",
     "summary": "Handbag discovery site. Trash bin near east stairwell."},
    {"id": "n_pharmacy", "label": "Harlow Pharmacy", "type": "location", "group": "poi",
     "summary": "Victim workplace. 200m from garage entrance."},
    {"id": "n_handbag", "label": "Handbag", "type": "evidence", "group": "physical",
     "summary": "Found in L1 bin at 07:45 PM. Contains wallet, keys missing."},
    {"id": "n_phone", "label": "Mobile Phone", "type": "evidence", "group": "digital",
     "summary": "Powered off at 06:59 PM. No signal since."},
    {"id": "n_vehicle", "label": "Victim Vehicle", "type": "evidence", "group": "physical",
     "summary": "Silver Volvo XC60. Still parked L3 when CCTV resumed."},
    {"id": "n_cctv", "label": "CCTV System", "type": "evidence", "group": "digital",
     "summary": "22-minute blind spot 06:58–07:20. Cause unknown."},
    {"id": "n_red_suv", "label": "Red SUV (unidentified)", "type": "evidence", "group": "vehicle",
     "summary": "Reported by Witness A only. No CCTV confirmation."},
    {"id": "n_silver_sedan", "label": "Silver Sedan", "type": "evidence", "group": "vehicle",
     "summary": "Reported by Witness B on L3 at 07:05 PM."},
    {"id": "n_doc42", "label": "Prescription Log #42", "type": "evidence", "group": "document",
     "summary": "Possibly tampered. Missing entries for Nov 12–16."},
    {"id": "n_narco", "label": "Narcotics Investigation", "type": "event", "group": "context",
     "summary": "Ongoing DEA probe into local prescription drug ring."},
    {"id": "n_staircase", "label": "Utility Staircase", "type": "location", "group": "poi",
     "summary": "Connects L3 to service exit. Not covered by CCTV."},
]

HARLOW_EDGES = [
    {"id": "e01", "source": "n_voss", "target": "n_garage", "type": "LOCATED_AT",
     "label": "Vehicle parked L3", "weight": 5, "certainty": "confirmed"},
    {"id": "e02", "source": "n_voss", "target": "n_handbag", "type": "OWNS",
     "label": "Personal belongings", "weight": 5, "certainty": "confirmed"},
    {"id": "e03", "source": "n_voss", "target": "n_phone", "type": "OWNS",
     "label": "Personal device", "weight": 5, "certainty": "confirmed"},
    {"id": "e04", "source": "n_voss", "target": "n_vehicle", "type": "OWNS",
     "label": "Registered owner", "weight": 5, "certainty": "confirmed"},
    {"id": "e05", "source": "n_voss", "target": "n_pharmacy", "type": "WORKS_AT",
     "label": "12 years employed", "weight": 4, "certainty": "confirmed"},
    {"id": "e06", "source": "n_vance", "target": "n_voss", "type": "COLLEAGUE_OF",
     "label": "Co-workers at pharmacy", "weight": 3, "certainty": "confirmed"},
    {"id": "e07", "source": "n_arthur", "target": "n_voss", "type": "MARRIED_TO",
     "label": "Spouse — 28 years", "weight": 4, "certainty": "confirmed"},
    {"id": "e08", "source": "n_handbag", "target": "n_garage_l1", "type": "FOUND_AT",
     "label": "In trash bin, east stairwell", "weight": 5, "certainty": "confirmed"},
    {"id": "e09", "source": "n_wit_a", "target": "n_red_suv", "type": "OBSERVED",
     "label": "07:15 PM, speeding away", "weight": 2, "certainty": "disputed"},
    {"id": "e10", "source": "n_wit_b", "target": "n_silver_sedan", "type": "OBSERVED",
     "label": "07:05 PM, idling L3", "weight": 3, "certainty": "disputed"},
    {"id": "e11", "source": "n_wit_c", "target": "n_garage", "type": "HEARD_AT",
     "label": "Argument, 07:12 PM, L2", "weight": 3, "certainty": "disputed"},
    {"id": "e12", "source": "n_cctv", "target": "n_garage", "type": "MONITORS",
     "label": "22-min gap detected", "weight": 5, "certainty": "confirmed"},
    {"id": "e13", "source": "n_voss", "target": "n_narco", "type": "LINKED_TO",
     "label": "Prescription irregularities", "weight": 2, "certainty": "suspected"},
    {"id": "e14", "source": "n_doc42", "target": "n_pharmacy", "type": "FILED_AT",
     "label": "Missing entries Nov 12-16", "weight": 3, "certainty": "suspected"},
    {"id": "e15", "source": "n_staircase", "target": "n_garage", "type": "CONNECTS_TO",
     "label": "Service exit, no CCTV", "weight": 4, "certainty": "confirmed"},
    {"id": "e16", "source": "n_garage_l1", "target": "n_garage", "type": "PART_OF",
     "label": "Same structure, different level", "weight": 5, "certainty": "confirmed"},
]

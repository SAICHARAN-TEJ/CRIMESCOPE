# SPDX-License-Identifier: AGPL-3.0-only
"""Shared test fixtures for CrimeScope test suite."""

import pytest

from backend.config import settings


@pytest.fixture
def sample_seed_packet():
    """A minimal seed packet for testing."""
    return {
        "title": "Test Case: Garage Incident",
        "victim": "Jane Doe",
        "location": "Harlow Street Garage",
        "date": "2026-03-15",
        "key_persons": [
            {"name": "John Smith", "role": "suspect", "credibility": 0.3},
            {"name": "Witness A", "role": "witness", "credibility": 0.8},
        ],
        "entities": [
            {"name": "Red SUV", "type": "vehicle", "description": "Seen departing at 7:15 PM", "confidence": 0.7},
            {"name": "Boot prints", "type": "evidence", "description": "Size 11, found on L3", "confidence": 0.85},
            {"name": "CCTV blackout", "type": "event", "description": "22-min outage from 6:58 PM", "confidence": 0.95},
        ],
        "key_evidence": [
            "22-minute CCTV blackout",
            "Boot prints size 11",
            "Red SUV departing 7:15 PM",
        ],
    }


@pytest.fixture
def sample_agent_votes():
    """Sample agent votes for voting/probable cause tests."""
    return [
        {"vote": {"hypothesis_id": "H-001", "confidence": 0.8}, "alignment_score": 0.7, "archetype": "Forensic Analyst"},
        {"vote": {"hypothesis_id": "H-001", "confidence": 0.9}, "alignment_score": 0.8, "archetype": "Contradiction Detector"},
        {"vote": {"hypothesis_id": "H-002", "confidence": 0.6}, "alignment_score": 0.5, "archetype": "Behavioral Profiler"},
        {"vote": {"hypothesis_id": "H-001", "confidence": 0.7}, "alignment_score": 0.6, "archetype": "Timeline Analyst"},
        {"vote": {"hypothesis_id": "H-003", "confidence": 0.4}, "alignment_score": 0.3, "archetype": "Alibi Verifier"},
    ]


@pytest.fixture
def sample_document_text():
    """A sample legal document for chunking/extraction tests."""
    return """
INCIDENT REPORT
Case Number: 2026-CR-1542
Date: March 15, 2026
Reporting Officer: Det. M. Rivera, Badge #4471

SECTION 1: INITIAL RESPONSE
At approximately 06:45 PM on March 15, 2026, officers were dispatched to
the Harlow Street parking garage following a 911 call from Witness A
reporting a disturbance on Level 2.

SECTION 2: SCENE DESCRIPTION
The parking garage is a 4-level structure with CCTV coverage. Upon arrival,
officers discovered a handbag in a trash receptacle on Level 1; wallet
intact but keys missing. Blood trace found on a pillar on Level 3.

SECTION 3: WITNESS STATEMENTS
Witness A (parking attendant) stated: "I heard loud voices on Level 2
around 7:10 PM. I saw a red SUV exit the south ramp at 7:15 PM."
Witness C (resident) stated: "I heard two people arguing. One male,
one female. It lasted about 3 minutes."

SECTION 4: EVIDENCE LOG
1. Handbag — recovered from L1 trash bin, fingerprints pending
2. Blood sample — L3 pillar, DNA analysis pending
3. Boot prints — size 11, photographed from L3 to utility staircase
4. Dark jacket — found on stairwell railing, not victim's wardrobe
"""

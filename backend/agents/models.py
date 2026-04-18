# SPDX-License-Identifier: AGPL-3.0-only
"""
Pydantic v2 models for CrimeScope swarm agents.

Every agent in the 1,000-agent swarm is represented by an AgentModel
instance carrying its identity, memory namespaces, causal chain, and vote.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentVote(BaseModel):
    hypothesis_id: str = "H-UNKNOWN"
    confidence: float = 0.0


class CausalStep(BaseModel):
    step: int
    event: str
    certainty: float = Field(ge=0.0, le=1.0)


class AgentModel(BaseModel):
    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    archetype: str = ""
    persona_description: str = ""
    case_id: str = ""
    episodic_memory_ns: str = ""
    semantic_memory_ns: str = ""
    evidence_alignment_score: float = 0.5
    current_causal_chain: List[CausalStep] = Field(default_factory=list)
    current_vote: AgentVote = Field(default_factory=AgentVote)

    def init_namespaces(self) -> None:
        """Set memory namespaces from case_id and agent_id."""
        self.episodic_memory_ns = f"case:{self.case_id}:agent:{self.agent_id}:episodic"
        self.semantic_memory_ns = f"case:{self.case_id}:agent:{self.agent_id}:semantic"


# ── Archetype definitions ────────────────────────────────────────────────

ARCHETYPES = [
    {
        "name": "Forensic Analyst",
        "count": 120,
        "role": "Physical evidence, trace materials, cause of death",
    },
    {
        "name": "Behavioral Profiler",
        "count": 100,
        "role": "Motive, psychology, pre-crime planning",
    },
    {
        "name": "Eyewitness Simulator",
        "count": 150,
        "role": "Timeline reconstruction from partial observational windows",
    },
    {
        "name": "Suspect Persona",
        "count": 200,
        "role": "Plausible perpetrator actions — deceptive + truthful variants",
    },
    {
        "name": "Alibi Verifier",
        "count": 80,
        "role": "Cross-check claimed timelines against physical constraints",
    },
    {
        "name": "Crime Scene Reconstructor",
        "count": 120,
        "role": "Spatial and temporal action sequencing",
    },
    {
        "name": "Statistical Baseline Agent",
        "count": 130,
        "role": "Base-rate crime statistics and demographic priors",
    },
    {
        "name": "Contradiction Detector",
        "count": 100,
        "role": "Hunt for inconsistencies across all other agents' outputs",
    },
]

assert sum(a["count"] for a in ARCHETYPES) == 1000, "Archetypes must sum to 1,000"

# SPDX-License-Identifier: AGPL-3.0-only
"""
Pydantic v2 schemas for the CrimeScope extraction pipelines.

Mode 1 (Vision): ForensicObservation → UnifiedSeedPacket
Mode 2 (Documents): StructuredExtract → ContradictionReport → UnifiedSeedPacket
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Shared entities ──────────────────────────────────────────────────────

class Entity(BaseModel):
    """A person, place, object, or event extracted from evidence."""
    name: str
    type: str = "unknown"  # person, location, evidence, event, vehicle, weapon
    description: str = ""
    aliases: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class KeyPerson(BaseModel):
    """A key individual identified in the investigation."""
    name: str
    role: str = ""  # victim, suspect, witness, associate
    description: str = ""
    alibi: str = ""
    motive: str = ""
    opportunity: str = ""


class TimelineConstraints(BaseModel):
    """Known temporal bounds of the incident."""
    earliest: str = ""
    latest: str = ""
    key_timestamps: List[Dict[str, str]] = Field(default_factory=list)


# ── Mode 1: Vision Pipeline ─────────────────────────────────────────────

class ForensicObservation(BaseModel):
    """Single observation from one image via the vision model."""
    image_index: int
    scene_description: str = ""
    objects_detected: List[str] = Field(default_factory=list)
    spatial_relationships: List[str] = Field(default_factory=list)
    anomalies: List[str] = Field(default_factory=list)
    blood_patterns: List[str] = Field(default_factory=list)
    trace_evidence: List[str] = Field(default_factory=list)
    environmental_conditions: str = ""
    estimated_time_of_day: str = ""


# ── Mode 2: Document Pipeline ───────────────────────────────────────────

class StructuredExtract(BaseModel):
    """Pass 1 output — entities and facts from documents."""
    entities: List[Entity] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    timeline: List[Dict[str, str]] = Field(default_factory=list)
    key_persons: List[KeyPerson] = Field(default_factory=list)
    raw_text_summary: str = ""


class Contradiction(BaseModel):
    """A single contradiction found between evidence sources."""
    source_a: str
    source_b: str
    claim_a: str
    claim_b: str
    severity: float = Field(ge=0.0, le=1.0, default=0.5)
    explanation: str = ""


class ContradictionReport(BaseModel):
    """Pass 2 output — contradictions found across documents."""
    contradictions: List[Contradiction] = Field(default_factory=list)
    reliability_scores: Dict[str, float] = Field(default_factory=dict)
    summary: str = ""


# ── Unified output ───────────────────────────────────────────────────────

class UnifiedSeedPacket(BaseModel):
    """The final seed packet fed to the 1,000-agent swarm."""
    title: str = ""
    description: str = ""
    mode: int = 1  # 1 = vision, 2 = documents, 3 = demo
    entities: List[Entity] = Field(default_factory=list)
    key_persons: List[KeyPerson] = Field(default_factory=list)
    timeline: TimelineConstraints = Field(default_factory=TimelineConstraints)
    facts: List[str] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    forensic_observations: List[ForensicObservation] = Field(default_factory=list)
    evidence_summary: str = ""
    initial_hypotheses: List[str] = Field(default_factory=list)


# ── Probable Cause Report ────────────────────────────────────────────────

class CausalStep(BaseModel):
    step: int
    event: str
    certainty: float = Field(ge=0.0, le=1.0)


class Hypothesis(BaseModel):
    id: str
    title: str
    probability: float = 0.0
    agent_count: int = 0
    causal_chain: List[CausalStep] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)


class ProbableCauseReport(BaseModel):
    """Final output of the Probable Cause Engine."""
    case_id: str
    title: str = "PROBABLE CAUSE REPORT"
    consensus: float = 0.0
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    consensus_facts: List[str] = Field(default_factory=list)
    dissent: List[Dict[str, str]] = Field(default_factory=list)
    agent_count: int = 1000
    rounds_completed: int = 30
    convergence_score: float = 0.0

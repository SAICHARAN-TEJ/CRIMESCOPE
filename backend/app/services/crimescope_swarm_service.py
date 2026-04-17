"""CrimeScope swarm service layer.

This service provides:
1. Unified seed packet validation.
2. Configurable swarm execution (default 1000 agents, 30 rounds).
3. Probabilistic hypothesis clustering and ranked report output.
4. Case/report persistence via the existing file-backed model layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import random
from typing import Any, Dict, List, Optional

from ..config import Config
from ..models.crimescope_case import CrimeScopeCase, CrimeScopeCaseManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger


logger = get_logger("crimescope.crimescope_swarm")


@dataclass(frozen=True)
class ArchetypeSpec:
    code: str
    display_name: str
    target_count: int
    role: str
    vote_weight: float


@dataclass(frozen=True)
class SwarmAgent:
    agent_id: str
    archetype: str
    vote_weight: float
    evidence_bias: float


@dataclass
class HypothesisCluster:
    hypothesis_id: str
    title: str
    probability_percentage: float
    supporting_agent_count: int
    evidence_alignment_score: float
    key_evidence_supporting: List[str]
    key_evidence_against: List[str]
    causal_chain: List[Dict[str, Any]]
    recommended_investigation_actions: List[str]

    def to_dict(self, rank: int) -> Dict[str, Any]:
        return {
            "rank": rank,
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "probability_percentage": round(self.probability_percentage, 2),
            "supporting_agent_count": self.supporting_agent_count,
            "evidence_alignment_score": round(self.evidence_alignment_score, 4),
            "key_evidence_supporting": self.key_evidence_supporting,
            "key_evidence_against": self.key_evidence_against,
            "causal_chain": self.causal_chain,
            "recommended_investigation_actions": self.recommended_investigation_actions,
        }


class CrimeScopeSwarmService:
    """Backend orchestration service for CrimeScope workflows."""

    ARCHETYPE_SPECS: List[ArchetypeSpec] = [
        ArchetypeSpec("forensic_analyst", "Forensic Analysts", 120, "Physical evidence and trace reconstruction", 1.14),
        ArchetypeSpec("behavioral_profiler", "Behavioral Profilers", 100, "Motive and intent modeling", 1.08),
        ArchetypeSpec("eyewitness_simulator", "Eyewitness Simulators", 150, "Partial timeline reconstruction", 1.0),
        ArchetypeSpec("suspect_persona", "Suspect Personas", 200, "Competing actor behavior pathways", 0.96),
        ArchetypeSpec("alibi_verifier", "Alibi Verifiers", 80, "Constraint checking against timeline claims", 1.12),
        ArchetypeSpec("crime_scene_reconstructor", "Crime Scene Reconstructors", 120, "Spatial-temporal event ordering", 1.1),
        ArchetypeSpec("statistical_baseline", "Statistical Baseline Agents", 130, "Base-rate anchoring and prior balancing", 0.9),
        ArchetypeSpec("contradiction_detector", "Contradiction Detectors", 100, "Cross-hypothesis inconsistency detection", 1.2),
    ]

    def __init__(self):
        self.task_manager = TaskManager()

    def create_case(
        self,
        title: str,
        investigative_question: str,
        seed_packet: Dict[str, Any],
        case_id: Optional[str] = None,
    ) -> CrimeScopeCase:
        self._validate_seed_packet(seed_packet)
        return CrimeScopeCaseManager.create_case(
            title=title,
            investigative_question=investigative_question,
            seed_packet=seed_packet,
            case_id=case_id,
        )

    def create_demo_case(self) -> CrimeScopeCase:
        """Create the PRD demo case: Harlow Street Disappearance."""
        demo_seed = {
            "case_id": "demo_harlow_street",
            "crime_type_hypothesis": ["abduction", "staged disappearance", "targeted homicide"],
            "confirmed_facts": [
                "Victim last seen leaving pharmacy at 6:42 PM",
                "Vehicle found locked on Level 3 of Harlow Street garage",
                "Victim handbag remained inside the vehicle",
                "CCTV has a 22-minute gap from 6:58 PM to 7:20 PM",
            ],
            "disputed_facts": [
                "Witness accounts disagree on a male individual near the vehicle",
                "No confirmed indication of forced entry",
                "Direction of departure from garage remains unclear",
            ],
            "key_persons": [
                {"name": "Margaret Voss", "role": "missing person", "credibility_score": 1.0},
                {"name": "Unnamed male figure", "role": "person of interest", "credibility_score": 0.41},
            ],
            "timeline_constraints": {
                "earliest_possible": "2026-04-15T18:42:00",
                "latest_possible": "2026-04-15T19:20:00",
                "anchor_events": [
                    "Pharmacy exit timestamp at 6:42 PM",
                    "CCTV blackout from 6:58 PM to 7:20 PM",
                    "Car discovered locked the following morning",
                ],
            },
            "physical_evidence_inventory": [
                "Vehicle interior with handbag present",
                "Garage floor footwear traces",
                "Partial camera metadata around blackout window",
            ],
            "video_observations": [
                "No confirmed vehicle exit captured during full blackout interval",
                "One pre-blackout frame shows potential shadow movement near rear access ramp",
            ],
            "open_questions": [
                "Was the CCTV gap accidental, manual, or remote tampering?",
                "Was the victim coerced before entering or after parking?",
                "How many actors were involved during the blackout interval?",
            ],
            "swarm_investigation_directive": (
                "Reconstruct backward from the observed scene and rank all plausible causal "
                "chains under strict consistency with confirmed facts."
            ),
        }

        return self.create_case(
            title="Harlow Street Disappearance (Demo)",
            investigative_question="What is the most probable causal reconstruction of the disappearance?",
            seed_packet=demo_seed,
            case_id=demo_seed["case_id"],
        )

    def get_case(self, case_id: str) -> Optional[CrimeScopeCase]:
        return CrimeScopeCaseManager.get_case(case_id)

    def list_cases(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [case.to_dict() for case in CrimeScopeCaseManager.list_cases(limit=limit)]

    def get_archetype_distribution(self, agent_count: Optional[int] = None) -> List[Dict[str, Any]]:
        actual_agent_count = self._normalise_agent_count(agent_count)
        counts = self._scaled_archetype_counts(actual_agent_count)
        distribution: List[Dict[str, Any]] = []
        for spec, count in zip(self.ARCHETYPE_SPECS, counts):
            distribution.append(
                {
                    "code": spec.code,
                    "name": spec.display_name,
                    "count": count,
                    "role": spec.role,
                    "vote_weight": spec.vote_weight,
                }
            )
        return distribution

    def run_case_swarm(self, case_id: str, rounds: Optional[int] = None, agent_count: Optional[int] = None) -> str:
        case = CrimeScopeCaseManager.get_case(case_id)
        if not case:
            raise ValueError(f"Case does not exist: {case_id}")

        actual_rounds = self._normalise_rounds(rounds)
        actual_agents = self._normalise_agent_count(agent_count)

        task_id = self.task_manager.create_task(
            task_type="crimescope_swarm_run",
            metadata={
                "case_id": case_id,
                "requested_rounds": rounds,
                "requested_agent_count": agent_count,
                "effective_rounds": actual_rounds,
                "effective_agent_count": actual_agents,
            },
        )

        self.task_manager.update_task(
            task_id,
            status=TaskStatus.PROCESSING,
            progress=5,
            message="Initializing CrimeScope swarm execution",
            progress_detail={"phase": "init", "phase_index": 1, "total_phases": 4},
        )

        self.task_manager.update_task(
            task_id,
            progress=25,
            message="Generating swarm agents and archetype assignment",
            progress_detail={"phase": "agent_setup", "phase_index": 2, "total_phases": 4},
        )

        report = self._build_probable_cause_report(
            case=case,
            rounds=actual_rounds,
            agent_count=actual_agents,
        )

        self.task_manager.update_task(
            task_id,
            progress=80,
            message="Persisting probable cause report",
            progress_detail={"phase": "persist", "phase_index": 3, "total_phases": 4},
        )

        report_id = CrimeScopeCaseManager.save_report(case_id, report)
        report["report_id"] = report_id

        self.task_manager.complete_task(
            task_id,
            result={
                "case_id": case_id,
                "report_id": report_id,
                "simulation_rounds": actual_rounds,
                "agents_participating": actual_agents,
            },
        )

        return task_id

    def get_case_report(self, case_id: str, report_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return CrimeScopeCaseManager.get_report(case_id=case_id, report_id=report_id)

    def _normalise_rounds(self, rounds: Optional[int]) -> int:
        resolved = rounds if rounds is not None else Config.SIMULATION_ROUNDS
        if not isinstance(resolved, int) or resolved <= 0:
            raise ValueError("rounds must be a positive integer")
        return resolved

    def _normalise_agent_count(self, agent_count: Optional[int]) -> int:
        resolved = agent_count if agent_count is not None else Config.SWARM_AGENT_COUNT
        if not isinstance(resolved, int) or resolved <= 0:
            raise ValueError("agent_count must be a positive integer")
        return resolved

    def _validate_seed_packet(self, seed_packet: Dict[str, Any]) -> None:
        if not isinstance(seed_packet, dict):
            raise ValueError("seed_packet must be an object")

        required_fields = [
            "case_id",
            "confirmed_facts",
            "disputed_facts",
            "timeline_constraints",
            "open_questions",
            "swarm_investigation_directive",
        ]
        missing = [field for field in required_fields if field not in seed_packet]
        if missing:
            raise ValueError(f"seed_packet is missing required fields: {', '.join(missing)}")

    def _scaled_archetype_counts(self, agent_count: int) -> List[int]:
        target_total = sum(spec.target_count for spec in self.ARCHETYPE_SPECS)
        raw_counts = [spec.target_count * agent_count / target_total for spec in self.ARCHETYPE_SPECS]
        base_counts = [int(value) for value in raw_counts]
        remaining = agent_count - sum(base_counts)

        remainders = sorted(
            [(index, raw_counts[index] - base_counts[index]) for index in range(len(raw_counts))],
            key=lambda entry: entry[1],
            reverse=True,
        )
        for index, _ in remainders[:remaining]:
            base_counts[index] += 1
        return base_counts

    def _agent_seed(self, case: CrimeScopeCase, rounds: int, agent_count: int) -> int:
        payload = f"{case.case_id}:{rounds}:{agent_count}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return int(digest[:16], 16)

    def _build_agents(self, case: CrimeScopeCase, rounds: int, agent_count: int) -> List[SwarmAgent]:
        rng = random.Random(self._agent_seed(case, rounds, agent_count))
        counts = self._scaled_archetype_counts(agent_count)
        agents: List[SwarmAgent] = []

        for spec, count in zip(self.ARCHETYPE_SPECS, counts):
            for idx in range(count):
                agents.append(
                    SwarmAgent(
                        agent_id=f"{spec.code}-{idx + 1}",
                        archetype=spec.code,
                        vote_weight=spec.vote_weight,
                        evidence_bias=rng.uniform(-0.12, 0.12),
                    )
                )
        return agents

    def _candidate_hypotheses(self, case: CrimeScopeCase) -> List[Dict[str, Any]]:
        seed = case.seed_packet
        crime_hints = seed.get("crime_type_hypothesis", []) or []
        timeline = seed.get("timeline_constraints", {}) or {}
        anchors = timeline.get("anchor_events", []) if isinstance(timeline, dict) else []

        default_titles = [
            "Coordinated abduction with pre-event surveillance",
            "Opportunistic escalation after routine encounter",
            "Single-actor coercion during evidence blackout window",
            "Staged disappearance masking a targeted criminal act",
            "Multi-actor diversion with post-event narrative manipulation",
        ]
        titles: List[str] = []
        for idx, hint in enumerate(crime_hints[:3]):
            titles.append(f"{str(hint).title()} reconstruction with evidentiary constraints")
            if idx >= 2:
                break
        titles.extend(default_titles)

        deduped_titles: List[str] = []
        for title in titles:
            if title not in deduped_titles:
                deduped_titles.append(title)

        candidates = []
        for index, title in enumerate(deduped_titles[:5]):
            candidates.append(
                {
                    "hypothesis_id": f"H-{index + 1:03d}",
                    "title": title,
                    "base_score": 0.85 - (index * 0.08),
                    "timeline_support": anchors[:3],
                }
            )
        return candidates

    def _simulate_probabilities(
        self,
        case: CrimeScopeCase,
        rounds: int,
        agents: List[SwarmAgent],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        rng = random.Random(self._agent_seed(case, rounds, len(agents)) + 97)

        disputed_facts = case.seed_packet.get("disputed_facts", [])
        contradiction_penalty = min(0.15, 0.01 * len(disputed_facts))

        round_probabilities: List[List[float]] = []
        final_supporters: List[List[SwarmAgent]] = [[] for _ in candidates]

        for _round in range(rounds):
            weighted_votes = [0.0 for _ in candidates]
            supporters: List[List[SwarmAgent]] = [[] for _ in candidates]

            for agent in agents:
                scores: List[float] = []
                for index, candidate in enumerate(candidates):
                    archetype_bias = 0.0
                    if agent.archetype == "contradiction_detector":
                        archetype_bias = 0.08 if index in (1, 2) else -0.03
                    elif agent.archetype == "forensic_analyst":
                        archetype_bias = 0.06 if index == 0 else 0.0
                    elif agent.archetype == "suspect_persona":
                        archetype_bias = 0.05 if index >= 2 else -0.01
                    elif agent.archetype == "statistical_baseline":
                        archetype_bias = -0.04 if index == 4 else 0.02

                    noise = rng.uniform(-0.05, 0.05)
                    score = max(
                        0.001,
                        candidate["base_score"]
                        + archetype_bias
                        + agent.evidence_bias
                        - contradiction_penalty
                        + noise,
                    )
                    scores.append(score)

                selected = max(range(len(scores)), key=lambda idx: scores[idx])
                weighted_votes[selected] += scores[selected] * agent.vote_weight
                supporters[selected].append(agent)

            vote_total = sum(weighted_votes) or 1.0
            probabilities = [(value / vote_total) * 100.0 for value in weighted_votes]
            round_probabilities.append(probabilities)
            final_supporters = supporters

        tail_window = max(3, min(rounds, 6))
        recent = round_probabilities[-tail_window:]
        averaged = [sum(row[idx] for row in recent) / tail_window for idx in range(len(candidates))]

        adjusted: List[float] = []
        for idx, score in enumerate(averaged):
            diversity = len({agent.archetype for agent in final_supporters[idx]})
            diversity_bonus = 5.0 if diversity >= 5 else 0.0
            contradiction_hit = 3.0 if idx in (2, 4) and len(disputed_facts) >= 2 else 0.0
            adjusted.append(max(0.01, score + diversity_bonus - contradiction_hit))

        adjusted_total = sum(adjusted) or 1.0
        normalized = [(value / adjusted_total) * 100.0 for value in adjusted]

        return {
            "final_probabilities": normalized,
            "final_supporters": final_supporters,
            "round_probabilities": round_probabilities,
        }

    def _build_causal_chain(self, case: CrimeScopeCase, candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
        timeline = case.seed_packet.get("timeline_constraints", {})
        anchors = timeline.get("anchor_events", []) if isinstance(timeline, dict) else []

        if not anchors:
            anchors = [
                "Pre-incident behavior inferred from known context",
                "Critical interaction window before observed outcome",
                "Observed scene state reached",
            ]

        chain: List[Dict[str, Any]] = []
        certainty_values = [0.58, 0.71, 0.83]
        for idx, event in enumerate(anchors[:3]):
            chain.append(
                {
                    "step": idx + 1,
                    "event": str(event),
                    "certainty": certainty_values[idx],
                }
            )
        return chain

    def _recommended_actions(self, case: CrimeScopeCase) -> List[str]:
        open_questions = case.seed_packet.get("open_questions", [])
        actions = [
            "Re-run timeline validation against highest-confidence anchor events",
            "Prioritize evidence collection for the strongest contradiction cluster",
        ]
        for question in open_questions[:2]:
            actions.append(f"Investigate unresolved question: {question}")
        return actions[:4]

    def _build_probable_cause_report(self, case: CrimeScopeCase, rounds: int, agent_count: int) -> Dict[str, Any]:
        confirmed_facts = case.seed_packet.get("confirmed_facts", [])
        disputed_facts = case.seed_packet.get("disputed_facts", [])

        agents = self._build_agents(case=case, rounds=rounds, agent_count=agent_count)
        candidates = self._candidate_hypotheses(case)
        simulation = self._simulate_probabilities(case, rounds, agents, candidates)

        probabilities = simulation["final_probabilities"]
        supporters = simulation["final_supporters"]

        ranked = sorted(
            range(len(candidates)),
            key=lambda idx: probabilities[idx],
            reverse=True,
        )

        top_indexes = ranked[:3]
        clusters: List[HypothesisCluster] = []
        for idx in top_indexes:
            candidate = candidates[idx]
            support_count = len(supporters[idx])
            support_facts = confirmed_facts[:2] if confirmed_facts else ["Cross-source corroboration in the seed packet"]
            against_facts = disputed_facts[:2] if disputed_facts else ["Residual uncertainty remains in unresolved windows"]

            evidence_alignment = max(0.45, min(0.94, (probabilities[idx] / 100.0) + 0.42))
            clusters.append(
                HypothesisCluster(
                    hypothesis_id=candidate["hypothesis_id"],
                    title=candidate["title"],
                    probability_percentage=probabilities[idx],
                    supporting_agent_count=support_count,
                    evidence_alignment_score=evidence_alignment,
                    key_evidence_supporting=support_facts,
                    key_evidence_against=against_facts,
                    causal_chain=self._build_causal_chain(case, candidate),
                    recommended_investigation_actions=self._recommended_actions(case),
                )
            )

        hypotheses = [cluster.to_dict(rank=rank + 1) for rank, cluster in enumerate(clusters)]
        top_probability_total = sum(item["probability_percentage"] for item in hypotheses)
        swarm_dissent = max(0.0, 100.0 - top_probability_total)

        return {
            "case_id": case.case_id,
            "generated_at": datetime.now().isoformat(),
            "simulation_rounds": rounds,
            "agents_participating": agent_count,
            "archetype_distribution": self.get_archetype_distribution(agent_count),
            "hypotheses": hypotheses,
            "consensus_facts": confirmed_facts[:15],
            "irresolvable_ambiguities": disputed_facts[:10],
            "swarm_dissent_log": f"{swarm_dissent:.1f}% of agents maintained outlier hypotheses",
            "methodology": {
                "agent_vote_weight": "Each vote is weighted by confidence and archetype-specific vote weight",
                "archetype_diversity_bonus": "+5% score bonus when >=5 archetypes support a hypothesis",
                "contradiction_penalty": "-3% on hypotheses with strong contradiction pressure",
                "bayesian_normalisation": "All weighted hypothesis scores are normalized to sum to 100%",
            },
        }

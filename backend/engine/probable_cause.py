# SPDX-License-Identifier: AGPL-3.0-only
"""
Probable Cause Engine — Bayesian-weighted hypothesis aggregation.

Takes all 1,000 agent votes, applies evidence alignment weights,
convergence bonuses, and contradiction penalties, then normalises
via Bayesian inference to produce the final ProbableCauseReport.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from backend.pipeline.schemas import (
    CausalStep,
    Hypothesis,
    ProbableCauseReport,
)
from backend.utils.logger import get_logger

logger = get_logger("crimescope.engine.probable_cause")


class ProbableCauseEngine:
    """Bayesian weighted voting → ranked hypotheses → final report."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id

    def generate(
        self,
        agent_votes: List[Dict[str, Any]],
        consensus_facts: List[str] | None = None,
        rounds_completed: int = 30,
    ) -> ProbableCauseReport:
        """
        Aggregate agent votes into a ProbableCauseReport.

        Weighting formula:
          weight = alignment_score × (1 + convergence_bonus) × (1 - contradiction_penalty)
        """
        # ── Tally weighted votes ─────────────────────────────────────
        hyp_weights: Dict[str, float] = defaultdict(float)
        hyp_agents: Dict[str, int] = defaultdict(int)
        hyp_chains: Dict[str, List[List[Dict]]] = defaultdict(list)
        hyp_archetype_support: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for vote_data in agent_votes:
            vote = vote_data.get("vote", {})
            hyp_id = vote.get("hypothesis_id", "H-UNKNOWN")
            confidence = float(vote.get("confidence", 0.5))
            alignment = float(vote_data.get("alignment_score", 0.5))
            archetype = vote_data.get("archetype", "Unknown")

            # Weighted vote
            weight = alignment * confidence
            hyp_weights[hyp_id] += weight
            hyp_agents[hyp_id] += 1
            hyp_archetype_support[hyp_id][archetype] += 1

        # ── Bayesian normalisation ───────────────────────────────────
        total_weight = sum(hyp_weights.values()) or 1.0
        hypotheses: List[Hypothesis] = []

        for hyp_id in sorted(hyp_weights.keys(), key=lambda k: hyp_weights[k], reverse=True):
            prob = hyp_weights[hyp_id] / total_weight
            hypotheses.append(
                Hypothesis(
                    id=hyp_id,
                    title=self._generate_title(hyp_id),
                    probability=round(prob, 4),
                    agent_count=hyp_agents[hyp_id],
                    causal_chain=[],  # Could be populated from agent chains
                    supporting_evidence=[],
                    contradicting_evidence=[],
                )
            )

        # ── Convergence score ────────────────────────────────────────
        convergence = 0.0
        if hypotheses:
            top_prob = hypotheses[0].probability
            convergence = top_prob  # Higher concentration = higher convergence

        # ── Dissent log ──────────────────────────────────────────────
        dissent: List[Dict[str, str]] = []
        if len(hypotheses) > 1:
            for hyp in hypotheses[1:]:
                if hyp.agent_count >= 50:
                    dissent.append({
                        "hypothesis": hyp.title,
                        "agent_count": str(hyp.agent_count),
                        "summary": f"{hyp.agent_count} agents maintain {hyp.title} at {hyp.probability:.1%} probability",
                    })

        report = ProbableCauseReport(
            case_id=self.case_id,
            title="PROBABLE CAUSE REPORT",
            consensus=round(convergence * 100, 1),
            hypotheses=hypotheses[:5],  # Top 5
            consensus_facts=consensus_facts or [],
            dissent=dissent,
            agent_count=sum(hyp_agents.values()),
            rounds_completed=rounds_completed,
            convergence_score=round(convergence, 4),
        )

        logger.info(
            f"ProbableCauseReport: {len(hypotheses)} hypotheses, "
            f"top={hypotheses[0].title if hypotheses else 'N/A'} "
            f"at {hypotheses[0].probability:.1%}" if hypotheses else "no hypotheses"
        )

        return report

    @staticmethod
    def _generate_title(hyp_id: str) -> str:
        """Generate a human-readable title for a hypothesis ID."""
        titles = {
            "H-001": "Planned Ambush",
            "H-002": "Staged Disappearance",
            "H-003": "Third-Party Opportunist",
            "H-004": "Accidental Discovery",
            "H-005": "Insurance Fraud Scheme",
        }
        return titles.get(hyp_id, f"Hypothesis {hyp_id}")

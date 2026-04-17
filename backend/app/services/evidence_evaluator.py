"""CrimeScope Evidence Evaluator.

Provides semantic scoring between evidence facts and hypothesis titles,
using lightweight keyword-overlap heuristics with weighted forensic term
boosting. Designed as a pure-Python, zero-dependency service layer that
can later be swapped for LLM-based embedding similarity.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Forensic term weight table
# Higher weight = stronger signal when term is shared between evidence + hyp.
# ---------------------------------------------------------------------------
_FORENSIC_WEIGHTS: Dict[str, float] = {
    # Physical evidence
    "fingerprint": 2.0, "dna": 2.5, "blood": 2.2, "trace": 1.8,
    "weapon": 2.0, "footprint": 1.8, "fibre": 1.7, "ballistic": 2.2,
    "toxicology": 2.0, "autopsy": 2.0, "wound": 1.9, "injury": 1.7,
    # Digital evidence
    "cctv": 1.9, "camera": 1.6, "footage": 1.8, "metadata": 1.7,
    "phone": 1.5, "gps": 1.8, "location": 1.6, "timestamp": 1.9,
    "email": 1.4, "text": 1.3, "message": 1.3,
    # Persons & roles
    "victim": 1.5, "suspect": 1.8, "witness": 1.6, "alibi": 2.1,
    "accomplice": 1.9, "perpetrator": 2.0, "person": 1.2,
    # Temporal
    "timeline": 1.8, "time": 1.3, "hour": 1.2, "window": 1.5,
    "before": 1.2, "after": 1.2, "during": 1.3, "gap": 1.7,
    # Event descriptors
    "abduction": 2.3, "homicide": 2.3, "robbery": 2.1, "assault": 2.0,
    "coercion": 1.9, "staged": 2.1, "disappearance": 2.0, "escape": 1.7,
    "premeditated": 2.2, "opportunistic": 1.9, "accidental": 1.8,
    # Motive
    "financial": 1.7, "insurance": 1.8, "debt": 1.6, "motive": 1.9,
    "relationship": 1.5, "dispute": 1.6,
    # Contradiction markers
    "inconsistent": 2.0, "contradiction": 2.0, "disputed": 1.9,
    "unverified": 1.6, "claimed": 1.4,
}


def _tokenize(text: str) -> List[str]:
    """Lowercase the text and extract alphabetic tokens."""
    return re.findall(r"[a-z]+", text.lower())


def _weighted_overlap(tokens_a: List[str], tokens_b: List[str]) -> float:
    """Return a weighted Jaccard-variant similarity score [0.0, 1.0]."""
    set_b = set(tokens_b)
    intersection_weight = sum(
        _FORENSIC_WEIGHTS.get(t, 1.0) for t in tokens_a if t in set_b
    )
    union_weight = sum(_FORENSIC_WEIGHTS.get(t, 1.0) for t in set(tokens_a) | set_b)
    if union_weight == 0:
        return 0.0
    return min(1.0, intersection_weight / union_weight)


class EvidenceEvaluator:
    """Stateless service that scores evidence-to-hypothesis alignment.

    Usage::

        score = EvidenceEvaluator.score_fact_against_hypothesis(
            fact="Victim handbag remained inside the vehicle",
            hypothesis_title="Staged disappearance masking a targeted criminal act",
        )
    """

    @staticmethod
    def score_fact_against_hypothesis(fact: str, hypothesis_title: str) -> float:
        """Return a [0.0, 1.0] alignment score for a single fact-hypothesis pair."""
        fact_tokens = _tokenize(fact)
        hyp_tokens = _tokenize(hypothesis_title)
        return _weighted_overlap(fact_tokens, hyp_tokens)

    @staticmethod
    def score_evidence_set(
        confirmed_facts: List[str],
        disputed_facts: List[str],
        hypothesis_title: str,
    ) -> Tuple[float, float]:
        """Score an entire evidence set for/against a hypothesis.

        Returns:
            (support_score, contradiction_score) both in [0.0, 1.0].
        """
        hyp_tokens = _tokenize(hypothesis_title)

        if confirmed_facts:
            support_scores = [
                _weighted_overlap(_tokenize(f), hyp_tokens) for f in confirmed_facts
            ]
            support_score = sum(support_scores) / len(support_scores)
        else:
            support_score = 0.0

        if disputed_facts:
            contra_scores = [
                _weighted_overlap(_tokenize(f), hyp_tokens) for f in disputed_facts
            ]
            contradiction_score = sum(contra_scores) / len(contra_scores)
        else:
            contradiction_score = 0.0

        return support_score, contradiction_score

    @staticmethod
    def rank_hypotheses_by_evidence(
        hypotheses: List[Dict[str, Any]],
        confirmed_facts: List[str],
        disputed_facts: List[str],
    ) -> List[Dict[str, Any]]:
        """Re-rank hypothesis dicts by their evidence alignment score.

        Each dict must have at least a ``title`` key.
        Returns the same dicts annotated with ``evidence_support``,
        ``evidence_contradiction``, and ``evidence_net_score`` keys,
        sorted descending by net score.
        """
        for h in hypotheses:
            title = h.get("title", "")
            support, contradiction = EvidenceEvaluator.score_evidence_set(
                confirmed_facts, disputed_facts, title
            )
            h["evidence_support"] = round(support, 4)
            h["evidence_contradiction"] = round(contradiction, 4)
            # Net score: support boosts, contradictions penalise (halved weight)
            h["evidence_net_score"] = round(
                max(0.0, support - contradiction * 0.5), 4
            )

        return sorted(hypotheses, key=lambda h: h["evidence_net_score"], reverse=True)

    @staticmethod
    def compute_evidentiary_strength(
        confirmed_facts: List[str],
        disputed_facts: List[str],
        open_questions: List[str],
    ) -> Dict[str, Any]:
        """Return a holistic evidentiary strength profile for a case.

        This aggregated metric is stored in the swarm report and used for
        UI rendering (e.g., confidence gauge).
        """
        n_confirmed = len(confirmed_facts)
        n_disputed = len(disputed_facts)
        n_open = len(open_questions)

        # Base strength from confirmed/disputed ratio
        total = n_confirmed + n_disputed
        confirmed_ratio = n_confirmed / total if total > 0 else 0.5

        # Penalise unresolved question load
        question_penalty = min(0.25, n_open * 0.03)

        raw_strength = confirmed_ratio - question_penalty
        strength_clamped = max(0.05, min(0.95, raw_strength))

        grade = (
            "STRONG" if strength_clamped >= 0.7
            else "MODERATE" if strength_clamped >= 0.45
            else "WEAK"
        )

        return {
            "score": round(strength_clamped, 3),
            "grade": grade,
            "confirmed_count": n_confirmed,
            "disputed_count": n_disputed,
            "open_questions_count": n_open,
            "confirmed_ratio": round(confirmed_ratio, 3),
            "question_penalty": round(question_penalty, 3),
        }

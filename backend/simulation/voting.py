"""
Hypothesis voting and clustering.

In production this would use embeddings + DBSCAN.
For the rebuild we use simplified consensus tallying.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List


def cluster_hypotheses(agent_outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Tally agent votes into hypothesis clusters and return
    the top 4 ranked by probability.
    """
    votes: Counter = Counter()

    for out in agent_outputs:
        raw = out.get("output", "")
        # Try to parse JSON votes from agent output
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            vote = parsed.get("vote", "H-UNKNOWN")
        except (json.JSONDecodeError, AttributeError):
            vote = "H-UNKNOWN"
        votes[vote] += 1

    total = max(sum(votes.values()), 1)
    clusters = []
    for hyp_id, count in votes.most_common(4):
        clusters.append(
            {
                "id": hyp_id,
                "title": _label(hyp_id),
                "probability": round(count / total, 3),
                "agent_count": count,
            }
        )

    return clusters or _default_clusters()


def _label(hyp_id: str) -> str:
    labels = {
        "H-001": "Planned Ambush",
        "H-002": "Staged Disappearance",
        "H-003": "Third-Party Opportunist",
        "H-004": "Accidental Discovery",
    }
    return labels.get(hyp_id, hyp_id.replace("H-", "Hypothesis "))


def _default_clusters() -> List[Dict[str, Any]]:
    """Fallback for demo / first round before votes exist."""
    return [
        {"id": "H-001", "title": "Planned Ambush", "probability": 0.45, "agent_count": 450},
        {"id": "H-002", "title": "Staged Disappearance", "probability": 0.30, "agent_count": 300},
        {"id": "H-003", "title": "Third-Party Opportunist", "probability": 0.15, "agent_count": 150},
        {"id": "H-004", "title": "Accidental Discovery", "probability": 0.10, "agent_count": 100},
    ]

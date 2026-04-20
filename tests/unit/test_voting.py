# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for the voting and probable cause modules."""

import pytest

from backend.simulation.voting import cluster_hypotheses
from backend.engine.probable_cause import ProbableCauseEngine


class TestVoting:
    """Tests for the hypothesis clustering/voting module."""

    def test_cluster_hypotheses_basic(self):
        """Should tally votes and return ranked clusters."""
        agent_outputs = [
            {"output": '{"vote": "H-001"}'},
            {"output": '{"vote": "H-001"}'},
            {"output": '{"vote": "H-002"}'},
            {"output": '{"vote": "H-001"}'},
            {"output": '{"vote": "H-003"}'},
        ]
        clusters = cluster_hypotheses(agent_outputs)
        assert len(clusters) > 0
        assert clusters[0]["id"] == "H-001"
        assert clusters[0]["probability"] == 0.6  # 3/5

    def test_cluster_hypotheses_empty(self):
        """Empty input should return default clusters."""
        clusters = cluster_hypotheses([])
        assert len(clusters) > 0
        assert clusters[0]["id"] == "H-001"

    def test_cluster_hypotheses_unknown_votes(self):
        """Unparseable votes should map to H-UNKNOWN."""
        agent_outputs = [
            {"output": "garbage data"},
            {"output": "more garbage"},
        ]
        clusters = cluster_hypotheses(agent_outputs)
        assert clusters[0]["id"] == "H-UNKNOWN"


class TestProbableCauseEngine:
    """Tests for the Bayesian hypothesis aggregation engine."""

    def test_generate_report(self, sample_agent_votes):
        """Should produce a valid ProbableCauseReport."""
        engine = ProbableCauseEngine("test-001")
        report = engine.generate(sample_agent_votes)
        assert report.case_id == "test-001"
        assert len(report.hypotheses) > 0
        assert report.agent_count == 5
        # Probabilities should sum to ~1.0
        total = sum(h.probability for h in report.hypotheses)
        assert 0.99 <= total <= 1.01

    def test_top_hypothesis_is_most_voted(self, sample_agent_votes):
        """The highest-weighted hypothesis should be ranked first."""
        engine = ProbableCauseEngine("test-001")
        report = engine.generate(sample_agent_votes)
        assert report.hypotheses[0].id == "H-001"

    def test_generate_with_empty_votes(self):
        """Empty votes should produce a report with no hypotheses."""
        engine = ProbableCauseEngine("test-002")
        report = engine.generate([])
        assert report.agent_count == 0

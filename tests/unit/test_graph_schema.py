# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for the graph schema models."""

import pytest

from backend.graph.schema import (
    GraphNode,
    PersonNode,
    LocationNode,
    EventNode,
    EvidenceNode,
    DocumentNode,
    GraphEdge,
    EvidencePath,
    EvidencePathStep,
    NodeType,
    EdgeType,
)


class TestNodeModels:
    def test_person_node(self):
        node = PersonNode(
            id="p1", name="Jane Doe", case_id="c1",
            role="victim", credibility=0.9, certainty=0.95,
        )
        assert node.node_type == NodeType.PERSON
        assert node.label == "Jane Doe"
        assert node.credibility == 0.9

    def test_location_node(self):
        node = LocationNode(
            id="l1", name="Garage", case_id="c1",
            location_type="indoor",
        )
        assert node.node_type == NodeType.LOCATION

    def test_event_node(self):
        node = EventNode(
            id="e1", name="CCTV Blackout", case_id="c1",
            timestamp="18:58", certainty=0.95,
        )
        assert node.node_type == NodeType.EVENT

    def test_evidence_node(self):
        node = EvidenceNode(
            id="ev1", name="Boot prints", case_id="c1",
            evidence_type="physical", certainty=0.85,
        )
        assert node.node_type == NodeType.EVIDENCE


class TestEdgeModel:
    def test_graph_edge(self):
        edge = GraphEdge(
            source="p1", target="e1",
            edge_type=EdgeType.INVOLVED_IN,
            certainty=0.8,
        )
        assert edge.edge_type == EdgeType.INVOLVED_IN
        assert edge.certainty == 0.8


class TestEvidencePath:
    def test_path_summarize(self):
        path = EvidencePath(
            steps=[
                EvidencePathStep(
                    node={"name": "John Smith", "type": "person", "certainty": 0.7},
                    edge={"type": "ASSOCIATED_WITH", "certainty": 0.6},
                    hop=0,
                ),
                EvidencePathStep(
                    node={"name": "Red SUV", "type": "vehicle", "certainty": 0.8},
                    hop=1,
                ),
            ],
            cumulative_certainty=0.75,
        )
        summary = path.summarize()
        assert "John Smith" in summary
        assert "Red SUV" in summary
        assert "ASSOCIATED_WITH" in summary
        assert path.length == 2

    def test_path_empty(self):
        path = EvidencePath()
        assert path.length == 0
        assert path.summarize() == ""

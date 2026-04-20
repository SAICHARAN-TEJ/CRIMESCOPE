"""
CrimeScope v4.0 — Unit Tests for Pydantic Schemas.

Validates all event models, API request/response models, and enum values.
"""

from __future__ import annotations

import pytest


class TestEnums:
    def test_event_types(self):
        from app.schemas.events import EventType

        assert EventType.JOB_STARTED == "JOB_STARTED"
        assert EventType.PIPELINE_COMPLETE == "PIPELINE_COMPLETE"
        assert len(EventType) == 9

    def test_job_status(self):
        from app.schemas.events import JobStatus

        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.PARTIAL == "partial"

    def test_agent_type(self):
        from app.schemas.events import AgentType

        assert AgentType.VIDEO == "video"
        assert AgentType.GRAPH == "graph"


class TestWSEvent:
    def test_ws_event_creation(self):
        from app.schemas.events import WSEvent, EventType

        event = WSEvent(
            event=EventType.AGENT_START,
            job_id="test-123",
            data={"agent_name": "video_agent"},
        )
        assert event.event == EventType.AGENT_START
        assert event.job_id == "test-123"
        assert event.timestamp is not None

    def test_ws_event_serialization(self):
        from app.schemas.events import WSEvent, EventType, AgentType

        event = WSEvent(
            event=EventType.AGENT_COMPLETE,
            job_id="job-456",
            agent=AgentType.ENTITY,
            data={"entities": 15, "processing_time_ms": 2500},
        )
        d = event.model_dump()
        assert d["event"] == "AGENT_COMPLETE"
        assert d["agent"] == "entity"


class TestGraphEvents:
    def test_graph_node_event(self):
        from app.schemas.events import GraphNodeEvent

        node = GraphNodeEvent(
            id="person-1",
            label="John Smith",
            type="Person",
            properties={"role": "suspect"},
        )
        assert node.id == "person-1"
        assert node.properties["role"] == "suspect"

    def test_graph_edge_event(self):
        from app.schemas.events import GraphEdgeEvent

        edge = GraphEdgeEvent(
            source="person-1",
            target="location-1",
            label="LOCATED_AT",
        )
        assert edge.source == "person-1"
        assert edge.label == "LOCATED_AT"


class TestAPIModels:
    def test_upload_init_request(self):
        from app.schemas.events import UploadInitRequest

        req = UploadInitRequest(filename="evidence.pdf")
        assert req.content_type == "application/octet-stream"

    def test_analysis_start_request(self):
        from app.schemas.events import AnalysisStartRequest, UploadCompleteRequest

        files = [
            UploadCompleteRequest(
                object_key="uploads/user1/abc/doc.pdf",
                filename="doc.pdf",
                content_type="application/pdf",
            )
        ]
        req = AnalysisStartRequest(files=files, question="Who is the suspect?")
        assert len(req.files) == 1
        assert req.job_id  # auto-generated

    def test_pipeline_result(self):
        from app.schemas.events import PipelineResult, JobStatus, AgentResult, AgentType

        result = PipelineResult(
            job_id="test",
            status=JobStatus.COMPLETED,
            agents=[
                AgentResult(agent=AgentType.ENTITY, success=True, entities=[{"id": "1"}]),
            ],
            total_entities=1,
        )
        assert result.status == JobStatus.COMPLETED
        assert len(result.agents) == 1

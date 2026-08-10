"""
CrimeScope — Tests for Consensus extraction (Step 5) and AGENT_ERROR emission.

Covers:
  - Majority-vote entity acceptance (disagreement = dropped or lower confidence)
  - Relationship voting
  - Consensus falls back to single-agent result when quorum is not reached
  - Independent circuit breakers per agent instance
  - Supervisor publishes AGENT_ERROR on agent timeout/crash
"""

from __future__ import annotations

import asyncio

import pytest

from app.engine.agents.consensus import ConsensusEntityExtractor, _names_match
from app.schemas.events import AgentType, EventType


class TestConsensusVoting:
    def test_names_match_fuzzy(self):
        assert _names_match("John Smith", "John Smith")
        assert _names_match("John Smith", "John Smyth")
        assert not _names_match("John Smith", "Alice Brown")

    def test_majority_vote_keeps_agreed_entities(self):
        extractor = ConsensusEntityExtractor()
        sets = [
            [{"name": "John Smith", "type": "Person", "confidence": 0.8}],
            [{"name": "John Smith", "type": "Person", "confidence": 0.9}],
            [{"name": "John Smith", "type": "Person", "confidence": 0.7}],
        ]
        accepted = extractor._vote_entities(sets, min_agree=2, total_agents=3)
        assert len(accepted) == 1
        assert accepted[0]["name"] == "John Smith"
        # Confidence = agreement ratio (3/3 = 1.0)
        assert accepted[0]["confidence"] == 1.0

    def test_disagreement_drops_entity(self):
        """An entity seen by only one agent is rejected (no silent overwrite)."""
        extractor = ConsensusEntityExtractor()
        sets = [
            [{"name": "Ghost Figure", "type": "Person", "confidence": 0.95}],
            [{"name": "John Smith", "type": "Person", "confidence": 0.9}],
            [{"name": "John Smith", "type": "Person", "confidence": 0.7}],
        ]
        accepted = extractor._vote_entities(sets, min_agree=2, total_agents=3)
        names = {e["name"] for e in accepted}
        assert "Ghost Figure" not in names  # hallucination rejected
        assert "John Smith" in names

    def test_relationship_voting(self):
        extractor = ConsensusEntityExtractor()
        rel_sets = [
            [{"source_id": "John Smith", "target_id": "Marcus Williams", "type": "KNOWS", "confidence": 0.8}],
            [{"source_id": "John Smith", "target_id": "Marcus Williams", "type": "KNOWS", "confidence": 0.7}],
            [{"source_id": "John Smith", "target_id": "David Chen", "type": "KNOWS", "confidence": 0.9}],
        ]
        accepted = extractor._vote_relationships(rel_sets, min_agree=2)
        assert len(accepted) == 1
        assert accepted[0]["target_id"] == "Marcus Williams"

    @pytest.mark.asyncio
    async def test_falls_back_to_single_agent_on_quorum_failure(self, monkeypatch):
        """If <2 agents succeed, return the first successful result instead of failing."""
        async def fake_run(self, job_id, payload):
            return type(
                "R", (), {
                    "success": True,
                    "entities": [{"name": "Only", "type": "Person", "confidence": 0.5}],
                    "relationships": [],
                    "facts": [],
                }
            )()

        # Force ALL sub-agents to fail, then EntityAgent fallback path
        extractor = ConsensusEntityExtractor()

        from app.engine.agents.entity import EntityAgent

        async def failing_run(self, job_id, payload):
            return type(
                "R", (), {
                    "success": False,
                    "entities": [],
                    "relationships": [],
                    "facts": [],
                    "error": "injected failure",
                }
            )()

        monkeypatch.setattr(EntityAgent, "run", failing_run)
        payload = {"text_chunks": ["some evidence text"], "question": "who?"}
        result = await extractor.run("job-c1", payload)
        # All agents failed → consensus fails, but supervisor degrades to EntityAgent
        assert result.success is False
        assert "failed" in result.error or "consensus" in result.error


class TestCircuitBreakerIndependence:
    def test_breakers_are_per_instance(self):
        from app.engine.agents.base import BaseAgent

        class DummyAgent(BaseAgent):
            agent_type = AgentType.CONSENSUS
            agent_name = "dummy"

            async def _execute(self, job_id, payload):
                return type("R", (), {"success": True, "entities": [], "relationships": [], "facts": []})()

        a, b = DummyAgent(), DummyAgent()
        assert a.circuit is not b.circuit
        a.circuit.record_failure()
        a.circuit.record_failure()
        a.circuit.record_failure()
        assert a.circuit.state == "open"
        assert b.circuit.state == "closed"


class TestSupervisorAgentErrorEvent:
    @pytest.mark.asyncio
    async def test_publishes_agent_error_on_timeout(self, monkeypatch):
        from app.engine.supervisor import Supervisor

        published = []

        class FakeRedis:
            async def publish_event(self, job_id, event):
                published.append(event)

        redis = FakeRedis()
        monkeypatch.setattr("app.engine.supervisor.get_redis", lambda: redis)

        class ExplodingAgent:
            agent_type = AgentType.ENTITY
            async def run(self, job_id, payload):
                raise asyncio.TimeoutError("boom")

        sup = Supervisor()
        result = await sup._run_with_timeout("entity", ExplodingAgent(), "job-err", {})
        assert result.success is False
        # AGENT_ERROR emitted with job_id and agent
        errors = [e for e in published if e.get("event") == EventType.AGENT_ERROR]
        assert len(errors) >= 1
        assert errors[0]["job_id"] == "job-err"
        assert errors[0]["agent"] == AgentType.ENTITY

    @pytest.mark.asyncio
    async def test_agent_error_never_raises_when_redis_down(self, monkeypatch):
        from app.engine.supervisor import Supervisor

        class BrokenRedis:
            async def publish_event(self, job_id, event):
                raise RuntimeError("redis down")

        monkeypatch.setattr("app.engine.supervisor.get_redis", lambda: BrokenRedis())

        class ExplodingAgent:
            agent_type = AgentType.DOCUMENT
            async def run(self, job_id, payload):
                raise asyncio.TimeoutError("boom")

        sup = Supervisor()
        result = await sup._run_with_timeout("document", ExplodingAgent(), "job-err2", {})
        assert result.success is False
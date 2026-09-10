"""
CrimeScope — Tests for persona materialization (Step 7) and persona chat.

Covers:
  - GraphPersonaAgent grounding: refuses to invent facts outside its record
  - materialize_graph_personas: only Person nodes, evidence refs attached
  - POST /analysis/{job_id}/personas endpoint: auth + ownership + response
  - Chat with persona_id routes to the graph persona (not ReportAgent)
"""

from __future__ import annotations

import pytest

from app.engine.agents.persona import GraphPersonaAgent, materialize_graph_personas

SUBGRAPH = {
    "nodes": [
        {"id": "person-1", "label": "Jennifer Williams", "type": "Person",
         "props": {"name": "Jennifer Williams", "role": "Witness",
                   "statement": "I saw a dark sedan leave at 22:30."}},
        {"id": "person-2", "label": "Marcus Williams", "type": "Person",
         "props": {"name": "Marcus Williams", "role": "Victim"}},
        {"id": "loc-1", "label": "Oakwood Drive", "type": "Location",
         "props": {"name": "Oakwood Drive"}},
    ],
    "edges": [
        {"source": "person-1", "target": "loc-1", "type": "LOCATED_AT"},
        {"source": "person-2", "target": "loc-1", "type": "LOCATED_AT"},
    ],
}


class TestGraphPersonaGrounding:
    def test_materializes_only_person_nodes(self):
        agents = materialize_graph_personas(SUBGRAPH, max_personas=10)
        assert len(agents) == 2
        assert {a.node_id for a in agents} == {"person-1", "person-2"}

    def test_persona_evidence_refs_include_connected_nodes(self):
        agent = next(a for a in materialize_graph_personas(SUBGRAPH) if a.node_id == "person-1")
        refs = agent._evidence_refs()
        assert "person-1" in refs
        assert "loc-1" in refs  # connected node cited

    def test_case_record_contains_only_stored_facts(self):
        agent = GraphPersonaAgent(
            node_id="person-1",
            person_name="Jennifer Williams",
            node_props={"role": "Witness", "statement": "saw a dark sedan"},
            connected=[],
            role_hint="Witness",
        )
        record = agent._case_record()
        assert "saw a dark sedan" in record
        assert "invented" not in record.lower()

    def test_materialize_respects_max(self):
        agents = materialize_graph_personas(SUBGRAPH, max_personas=1)
        assert len(agents) == 1

    @pytest.mark.asyncio
    async def test_persona_rejects_empty_question(self):
        """Empty message → failed result (BaseAgent wraps the exception)."""
        agent = GraphPersonaAgent("person-1", "Jennifer Williams", {}, [], "Witness")
        result = await agent.run("job-p1", {"message": ""})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_persona_runs_with_fallback(self):
        """No LLM key → persona still returns a grounded fallback reply."""
        agent = GraphPersonaAgent(
            node_id="person-1",
            person_name="Jennifer Williams",
            node_props={"role": "Witness", "statement": "saw a dark sedan leave at 22:30"},
            connected=[{"relation": "LOCATED_AT", "target": "Oakwood Drive"}],
            role_hint="Witness",
        )
        result = await agent.run("job-p1", {"message": "What did you see?"})
        assert result.success
        payload = result.entities[0]
        assert payload["persona_id"] == "person-1"
        assert "LOCATED_AT" in agent._case_record()


class TestPersonaEndpoints:


    def test_materialize_unknown_job_404(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        token = client.post(
            "/api/v1/auth/token",
            json={"username": "admin", "password": "crimescope"},
        ).json()["access_token"]
        resp = client.post(
            "/api/v1/analysis/nope/personas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_chat_with_unknown_persona_404(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        token = client.post(
            "/api/v1/auth/token",
            json={"username": "admin", "password": "crimescope"},
        ).json()["access_token"]
        resp = client.post(
            "/api/v1/chat",
            json={"job_id": "nope", "message": "hi", "persona_id": "ghost"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

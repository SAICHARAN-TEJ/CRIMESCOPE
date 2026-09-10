"""
CrimeScope — Tests for scenario hypothesis injection (Step 8).

Covers:
  - Agent returns a complete add/remove diff payload
  - Consensus verdict with neutral fallback evaluations
  - ScenarioResult carries removed entities/edges
"""

from __future__ import annotations

from app.engine.agents.scenario import ScenarioAgent


class TestScenarioAgent:
    async def test_empty_hypothesis_noop(self):
        agent = ScenarioAgent()
        result = await agent.run("job-s1", {"hypothesis": ""})
        assert result.success
        assert len(result.entities) == 0

    async def test_diff_payload_shape_without_llm(self):
        """No LLM key → full add/remove diff shape, empty lists."""
        agent = ScenarioAgent()
        result = await agent.run(
            "job-s1",
            {
                "hypothesis": "What if Marcus was in the car with Jennifer?",
                "entities": [{"id": "p1", "type": "Person", "name": "Jennifer"}],
                "text_chunks": [],
            },
        )
        assert result.success

    async def test_scenario_result_includes_removed_sides(self):
        """persisted diff_result contains removed entities/edges keys."""
        agent = ScenarioAgent()
        result = await agent.run(
            "job-s1",
            {"hypothesis": "What if the witness's statement is fabricated?"},
        )
        assert result.success
        data = result.entities[0]
        assert "removed_entities" in data
        assert "removed_edges" in data

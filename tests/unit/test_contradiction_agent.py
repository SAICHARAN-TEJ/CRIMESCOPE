# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for ContradictionAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.agents.functional.contradiction_agent import ContradictionAgent
from backend.agents.functional.base import AgentInput


@pytest.fixture
def contradiction_agent():
    return ContradictionAgent()


@pytest.fixture
def sample_input():
    return AgentInput(
        case_id="test-001",
        raw_texts=[
            "Witness A stated the suspect was wearing a blue jacket and left at 10:30 PM.",
            "Witness B confirmed the suspect wore a red shirt and departed around 11:00 PM.",
        ],
        video_transcripts=[
            {
                "video_index": 0,
                "segments": [
                    {"start": 0.0, "end": 5.0, "text": "Person in dark hoodie exits at 10:45 PM"},
                ],
            }
        ],
        metadata={
            "entities": [
                {"name": "Suspect", "type": "person", "description": "Main suspect"},
                {"name": "5th Avenue", "type": "location", "description": "Scene"},
            ]
        },
    )


class TestContradictionAgent:
    def test_name(self, contradiction_agent):
        assert contradiction_agent.name == "contradiction_agent"

    @pytest.mark.asyncio
    async def test_empty_input(self, contradiction_agent):
        empty = AgentInput(case_id="test-empty")
        result = await contradiction_agent.process(empty)
        assert result.success is False
        assert "No evidence" in result.error

    def test_summarize_docs(self, contradiction_agent, sample_input):
        summary = contradiction_agent._summarize_docs(sample_input.raw_texts)
        assert "Witness" in summary or "stated" in summary

    def test_format_entities(self, contradiction_agent, sample_input):
        formatted = contradiction_agent._format_entities(
            sample_input.metadata["entities"]
        )
        assert "Suspect" in formatted
        assert "5th Avenue" in formatted

    @pytest.mark.asyncio
    async def test_process_with_mock_llm(self, contradiction_agent, sample_input):
        mock_response = '''{
            "contradictions": [
                {
                    "type": "factual",
                    "claim_a": "blue jacket",
                    "source_a": "witness_a",
                    "claim_b": "red shirt",
                    "source_b": "witness_b",
                    "severity": 0.8,
                    "explanation": "Conflicting clothing description",
                    "forensic_significance": "high",
                    "possible_resolution": "Different lighting conditions"
                },
                {
                    "type": "temporal",
                    "claim_a": "left at 10:30 PM",
                    "source_a": "witness_a",
                    "claim_b": "departed around 11:00 PM",
                    "source_b": "witness_b",
                    "severity": 0.6,
                    "explanation": "30-minute discrepancy in departure time",
                    "forensic_significance": "medium",
                    "possible_resolution": "Approximate vs exact time"
                }
            ],
            "fabrication_indicators": [],
            "verified_claims": [
                {"claim": "Suspect left the premises", "sources": ["witness_a", "witness_b", "video_0"], "confidence": 0.95}
            ],
            "summary": "Two key contradictions found: clothing and timing"
        }'''

        with patch("backend.agents.functional.contradiction_agent.openrouter") as mock_or:
            mock_or.chat = AsyncMock(return_value=mock_response)
            result = await contradiction_agent.process(sample_input)

        assert result.success is True
        assert result.agent_name == "contradiction_agent"
        assert len(result.contradictions) == 2
        assert result.contradictions[0]["severity"] == 0.8
        assert len(result.relationships) >= 2  # CONTRADICTS + CORROBORATES edges
        assert any("HIGH-SEVERITY" in f for f in result.facts)

# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for SynthesisAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.agents.functional.synthesis_agent import SynthesisAgent
from backend.agents.functional.base import AgentInput


@pytest.fixture
def synthesis_agent():
    return SynthesisAgent()


@pytest.fixture
def populated_input():
    """Input with metadata from upstream agents."""
    return AgentInput(
        case_id="test-001",
        metadata={
            "all_entities": [
                {"name": "John Smith", "type": "person", "description": "Suspect", "confidence": 0.9},
                {"name": "5th Avenue", "type": "location", "description": "Crime scene", "confidence": 0.95},
            ],
            "all_timeline": [
                {"time": "2024-01-15T22:30", "event": "Suspect observed leaving", "source": "doc_0"},
                {"time": "2024-01-16T07:00", "event": "Red SUV seen at scene", "source": "doc_0"},
            ],
            "all_contradictions": [
                {"claim_a": "blue jacket", "claim_b": "red shirt", "severity": 0.8},
            ],
            "all_facts": [
                "Extracted 2 entities",
                "Timeline spans 8.5 hours",
                "1 HIGH-SEVERITY contradiction detected",
            ],
            "all_legal": [
                {"type": "probable_cause", "charges": ["trespassing"]},
            ],
            "correlations_text": "Video corroborates suspect presence at 10:45 PM",
        },
    )


class TestSynthesisAgent:
    def test_name(self, synthesis_agent):
        assert synthesis_agent.name == "synthesis_agent"

    @pytest.mark.asyncio
    async def test_empty_input(self, synthesis_agent):
        empty = AgentInput(case_id="test-empty")
        result = await synthesis_agent.process(empty)
        assert result.success is False
        assert "No agent outputs" in result.error

    @pytest.mark.asyncio
    async def test_process_with_mock_llm(self, synthesis_agent, populated_input):
        mock_response = '''{
            "executive_summary": "Investigation reveals suspect John Smith was present at 5th Avenue on the night of January 15. Multiple witnesses and video evidence confirm his presence.",
            "key_findings": ["Suspect confirmed at scene", "Timeline gap of 8.5 hours", "Clothing contradiction between witnesses"],
            "evidence_chain": [
                {"from": "Witness A", "to": "Video footage", "connection": "Both confirm suspect departure", "strength": 0.9}
            ],
            "hypotheses": [
                {"rank": 1, "description": "Suspect committed trespassing", "probability": 0.75, "supporting_evidence": ["witness testimony", "video"], "weaknesses": ["clothing contradiction"]},
                {"rank": 2, "description": "Suspect was a bystander", "probability": 0.20, "supporting_evidence": ["no direct evidence of crime"], "weaknesses": ["presence at scene"]}
            ],
            "contradictions_summary": "One high-severity contradiction in clothing description",
            "recommended_actions": ["Interview witnesses again about clothing", "Enhance video footage"],
            "overall_confidence": 0.72,
            "report_quality_notes": "Limited by 2-source evidence base"
        }'''

        with patch("backend.agents.functional.synthesis_agent.openrouter") as mock_or:
            mock_or.chat = AsyncMock(return_value=mock_response)
            result = await synthesis_agent.process(populated_input)

        assert result.success is True
        assert result.agent_name == "synthesis_agent"
        assert len(result.facts) >= 4
        assert any("hypotheses" in f.lower() for f in result.facts)
        assert len(result.legal_findings) == 1
        assert result.legal_findings[0]["type"] == "synthesis_report"
        assert len(result.legal_findings[0]["hypotheses"]) == 2
        assert result.legal_findings[0]["overall_confidence"] == 0.72

    def test_format_entities(self, synthesis_agent):
        entities = [
            {"name": "Alice", "type": "person", "description": "Witness", "confidence": 0.9},
        ]
        text = synthesis_agent._format_entities(entities)
        assert "Alice" in text
        assert "person" in text

    def test_format_timeline(self, synthesis_agent):
        events = [
            {"time": "10:30 PM", "event": "Suspect left", "source": "doc_0"},
        ]
        text = synthesis_agent._format_timeline(events)
        assert "10:30 PM" in text
        assert "Suspect left" in text

    def test_format_contradictions(self, synthesis_agent):
        contras = [
            {"claim_a": "blue jacket", "claim_b": "red shirt", "severity": 0.8},
        ]
        text = synthesis_agent._format_contradictions(contras)
        assert "blue jacket" in text

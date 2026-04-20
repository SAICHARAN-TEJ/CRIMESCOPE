# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for TimelineAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.agents.functional.timeline_agent import TimelineAgent
from backend.agents.functional.base import AgentInput


@pytest.fixture
def timeline_agent():
    return TimelineAgent()


@pytest.fixture
def sample_input():
    return AgentInput(
        case_id="test-001",
        raw_texts=[
            "On January 15, 2024, at approximately 10:30 PM, Officer Smith observed "
            "the suspect leaving the premises. The next morning, witnesses confirmed "
            "seeing a red SUV parked at the location around 7:00 AM.",
            "The victim was last seen on Monday evening at the coffee shop on 5th Avenue. "
            "According to witness testimony, the suspect arrived at approximately 9:45 PM.",
        ],
        video_transcripts=[
            {
                "video_index": 0,
                "transcript": "Surveillance footage from the parking lot",
                "segments": [
                    {"start": 0.0, "end": 5.0, "text": "A person enters the parking lot"},
                    {"start": 30.0, "end": 35.0, "text": "The red SUV arrives"},
                    {"start": 120.0, "end": 125.0, "text": "Two people exit the vehicle"},
                ],
            }
        ],
    )


class TestTimelineAgent:
    def test_name(self, timeline_agent):
        assert timeline_agent.name == "timeline_agent"

    @pytest.mark.asyncio
    async def test_empty_input(self, timeline_agent):
        empty = AgentInput(case_id="test-empty")
        result = await timeline_agent.process(empty)
        assert result.success is False
        assert "No temporal evidence" in result.error

    def test_build_evidence_text(self, timeline_agent, sample_input):
        text = timeline_agent._build_evidence_text(sample_input.raw_texts)
        assert "January 15" in text or "Document 0" in text
        assert len(text) > 0

    def test_build_video_timestamps(self, timeline_agent, sample_input):
        ts = timeline_agent._build_video_timestamps(sample_input.video_transcripts)
        assert "Video 0" in ts
        assert "parking lot" in ts

    @pytest.mark.asyncio
    async def test_process_with_mock_llm(self, timeline_agent, sample_input):
        mock_response = '''{
            "events": [
                {"timestamp": "2024-01-15T22:30:00", "description": "Suspect observed leaving", "participants": ["suspect"], "location": "premises", "source": "document_0", "confidence": 0.9, "is_approximate": false},
                {"timestamp": "2024-01-16T07:00:00", "description": "Red SUV seen", "participants": ["witnesses"], "location": "premises", "source": "document_0", "confidence": 0.8, "is_approximate": true}
            ],
            "temporal_gaps": [{"start": "22:30", "end": "07:00", "significance": "high", "note": "Overnight gap"}],
            "conflicting_timestamps": [],
            "earliest_event": "2024-01-15T22:30:00",
            "latest_event": "2024-01-16T07:00:00",
            "total_span": "8.5 hours"
        }'''

        with patch("backend.agents.functional.timeline_agent.openrouter") as mock_or:
            mock_or.chat = AsyncMock(return_value=mock_response)
            result = await timeline_agent.process(sample_input)

        assert result.success is True
        assert result.agent_name == "timeline_agent"
        assert len(result.timeline_events) == 2
        assert result.timeline_events[0]["time"] == "2024-01-15T22:30:00"
        assert len(result.relationships) >= 1  # FOLLOWED_BY edges
        assert any("timeline" in f.lower() or "events" in f.lower() for f in result.facts)

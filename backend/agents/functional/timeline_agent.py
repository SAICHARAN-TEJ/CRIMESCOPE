# SPDX-License-Identifier: AGPL-3.0-only
"""
Timeline Agent — constructs a chronological sequence of events from
all evidence sources (documents, video transcripts, audio segments).

Responsibilities:
  - Extract temporal references from all input sources
  - Normalise dates/times to ISO format where possible
  - Resolve relative time references ("the next day", "30 minutes later")
  - Merge and deduplicate events from multiple sources
  - Detect temporal gaps where evidence is missing
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from backend.agents.functional.base import FunctionalAgent, AgentInput, AgentOutput
from backend.config import settings
from backend.llm import ModelRouter
from backend.utils.openrouter import openrouter
from backend.utils.logger import get_logger

logger = get_logger("crimescope.agent.timeline")

TIMELINE_PROMPT = """You are a forensic timeline reconstruction specialist.

EVIDENCE SOURCES:
{evidence_text}

VIDEO/AUDIO TIMESTAMPS:
{video_timestamps}

Construct a comprehensive chronological timeline of ALL events mentioned.
For each event, identify:
1. The exact or approximate time (ISO 8601 where possible)
2. What happened
3. Who was involved
4. Where it occurred
5. The source of this information (document X, video timestamp Y)
6. Confidence level (0.0-1.0)

Also identify:
- TEMPORAL GAPS: periods where no evidence exists
- RELATIVE REFERENCES: phrases like "the next morning" that need anchoring
- CONFLICTING TIMESTAMPS: same event with different times from different sources

Return JSON:
{{
  "events": [
    {{
      "timestamp": "ISO 8601 or approximate",
      "description": "what happened",
      "participants": ["who"],
      "location": "where",
      "source": "document_0 / video_1 / audio",
      "confidence": 0.0-1.0,
      "is_approximate": true
    }}
  ],
  "temporal_gaps": [
    {{"start": "...", "end": "...", "significance": "high|medium|low", "note": "..."}}
  ],
  "conflicting_timestamps": [
    {{"event": "...", "time_a": "...", "source_a": "...", "time_b": "...", "source_b": "...", "resolution": "..."}}
  ],
  "earliest_event": "ISO 8601",
  "latest_event": "ISO 8601",
  "total_span": "human readable duration"
}}"""


class TimelineAgent(FunctionalAgent):
    name = "timeline_agent"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        start = time.time()

        evidence_text = self._build_evidence_text(input_data.raw_texts)
        video_timestamps = self._build_video_timestamps(input_data.video_transcripts)

        if not evidence_text and not video_timestamps:
            return self._empty_output("No temporal evidence available")

        try:
            prompt = TIMELINE_PROMPT.format(
                evidence_text=evidence_text[:4000],
                video_timestamps=video_timestamps[:2000],
            )
            raw = await openrouter.chat(
                settings.fast_model_name,
                prompt,
                system="You are a forensic chronologist. Return only valid JSON.",
            )
            parsed = ModelRouter.parse_json_safe(raw)
        except Exception as e:
            logger.warning(f"Timeline LLM call failed: {e}")
            parsed = None

        elapsed = (time.time() - start) * 1000

        if not parsed:
            return AgentOutput(
                agent_name=self.name,
                success=False,
                error="Timeline reconstruction failed",
                processing_time_ms=elapsed,
            )

        # Extract structured timeline events
        events = parsed.get("events", [])
        timeline_events = []
        for ev in events:
            timeline_events.append({
                "time": ev.get("timestamp", "unknown"),
                "event": ev.get("description", ""),
                "participants": ev.get("participants", []),
                "location": ev.get("location", ""),
                "source": ev.get("source", "unknown"),
                "confidence": ev.get("confidence", 0.5),
                "is_approximate": ev.get("is_approximate", True),
            })

        # Sort by timestamp (best effort — some may not parse)
        timeline_events.sort(key=lambda e: e.get("time", "zzz"))

        # Build facts summary
        facts = [
            f"Reconstructed timeline with {len(events)} events",
            f"Span: {parsed.get('earliest_event', '?')} → {parsed.get('latest_event', '?')}",
            f"Duration: {parsed.get('total_span', 'unknown')}",
            f"Found {len(parsed.get('temporal_gaps', []))} temporal gaps",
            f"Found {len(parsed.get('conflicting_timestamps', []))} timestamp conflicts",
        ]

        # Build relationships for graph (temporal edges)
        relationships = []
        for i in range(len(timeline_events) - 1):
            relationships.append({
                "source": timeline_events[i].get("event", "")[:50],
                "target": timeline_events[i + 1].get("event", "")[:50],
                "type": "FOLLOWED_BY",
                "properties": {
                    "time_gap": f"{timeline_events[i].get('time', '')} → {timeline_events[i+1].get('time', '')}",
                },
            })

        return AgentOutput(
            agent_name=self.name,
            success=True,
            timeline_events=timeline_events,
            relationships=relationships,
            contradictions=parsed.get("conflicting_timestamps", []),
            facts=facts,
            raw_output=json.dumps(parsed, indent=2)[:3000],
            processing_time_ms=elapsed,
        )

    def _build_evidence_text(self, texts: List[str]) -> str:
        """Extract time-relevant passages from documents."""
        parts = []
        time_keywords = [
            "am", "pm", "o'clock", "approximately", "around", "between",
            "before", "after", "during", "at ", "on ", "january", "february",
            "march", "april", "may", "june", "july", "august", "september",
            "october", "november", "december", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday", "sunday", "morning", "afternoon",
            "evening", "night", "midnight", "noon", "yesterday", "today",
        ]
        for i, text in enumerate(texts[:5]):
            lines = text.split("\n")
            temporal_lines = [
                l.strip() for l in lines
                if len(l.strip()) > 20
                and any(k in l.lower() for k in time_keywords)
            ]
            if temporal_lines:
                parts.append(f"[Document {i}]\n" + "\n".join(temporal_lines[:15]))
            elif text.strip():
                # Include first few lines anyway for context
                parts.append(f"[Document {i}]\n" + "\n".join(lines[:5]))
        return "\n\n".join(parts)

    def _build_video_timestamps(self, transcripts: List[Dict[str, Any]]) -> str:
        """Format video transcript segments with timestamps."""
        parts = []
        for vt in transcripts:
            idx = vt.get("video_index", 0)
            segments = vt.get("segments", [])
            if segments:
                seg_lines = [
                    f"  [{s['start']:.1f}s] {s['text']}"
                    for s in segments[:25]
                ]
                parts.append(f"[Video {idx} timestamps]\n" + "\n".join(seg_lines))
            elif vt.get("transcript"):
                parts.append(f"[Video {idx}] {vt['transcript'][:500]}")
        return "\n\n".join(parts)

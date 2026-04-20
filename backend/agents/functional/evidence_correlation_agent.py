# SPDX-License-Identifier: AGPL-3.0-only
"""
Evidence Correlation Agent — cross-references video/audio timestamps
with document claims to find corroborations and contradictions.
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

logger = get_logger("crimescope.agent.evidence_correlation")

CORRELATION_PROMPT = """You are a forensic evidence correlation specialist.

DOCUMENT CLAIMS:
{doc_claims}

VIDEO/AUDIO EVIDENCE:
{video_evidence}

Cross-reference the document claims with the video/audio evidence.
Identify:
1. CORROBORATIONS: claims supported by video/audio
2. CONTRADICTIONS: claims contradicted by video/audio
3. GAPS: claims with no corresponding video/audio evidence
4. TIMELINE CONFLICTS: temporal inconsistencies

Return JSON:
{{
  "corroborations": [
    {{"claim": "...", "video_evidence": "...", "timestamp": "...", "confidence": 0.0-1.0}}
  ],
  "contradictions": [
    {{"claim_a": "...", "claim_b": "...", "source_a": "document", "source_b": "video", "severity": 0.0-1.0, "explanation": "..."}}
  ],
  "gaps": [
    {{"claim": "...", "source": "...", "significance": "high|medium|low"}}
  ],
  "timeline_conflicts": [
    {{"event_a": "...", "time_a": "...", "event_b": "...", "time_b": "...", "conflict": "..."}}
  ]
}}"""


class EvidenceCorrelationAgent(FunctionalAgent):
    name = "evidence_correlation_agent"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        start = time.time()

        # Build document claims summary
        doc_claims = self._summarize_docs(input_data.raw_texts)
        video_evidence = self._summarize_videos(input_data.video_transcripts)

        if not doc_claims and not video_evidence:
            return self._empty_output("No evidence to correlate")

        # Run correlation via LLM
        try:
            prompt = CORRELATION_PROMPT.format(
                doc_claims=doc_claims[:3000],
                video_evidence=video_evidence[:3000],
            )
            raw = await openrouter.chat(
                settings.reasoning_model_name,
                prompt,
                system="You are a forensic evidence analyst. Return only valid JSON.",
            )
            parsed = ModelRouter.parse_json_safe(raw)
        except Exception as e:
            logger.warning(f"Evidence correlation LLM call failed: {e}")
            parsed = None

        elapsed = (time.time() - start) * 1000

        if not parsed:
            return AgentOutput(
                agent_name=self.name,
                success=False,
                error="Correlation analysis failed",
                processing_time_ms=elapsed,
            )

        # Build relationships for graph
        relationships = []
        contradictions = parsed.get("contradictions", [])
        for c in contradictions:
            relationships.append({
                "source": c.get("source_a", "document"),
                "target": c.get("source_b", "video"),
                "type": "CONTRADICTS",
                "properties": {
                    "claim_a": c.get("claim_a", ""),
                    "claim_b": c.get("claim_b", ""),
                    "severity": c.get("severity", 0.5),
                },
            })

        for corr in parsed.get("corroborations", []):
            relationships.append({
                "source": "document",
                "target": "video",
                "type": "CORROBORATES",
                "properties": {
                    "claim": corr.get("claim", ""),
                    "evidence": corr.get("video_evidence", ""),
                    "confidence": corr.get("confidence", 0.5),
                },
            })

        return AgentOutput(
            agent_name=self.name,
            success=True,
            relationships=relationships,
            contradictions=contradictions,
            facts=[
                f"Found {len(parsed.get('corroborations', []))} corroborations",
                f"Found {len(contradictions)} contradictions",
                f"Found {len(parsed.get('gaps', []))} evidence gaps",
                f"Found {len(parsed.get('timeline_conflicts', []))} timeline conflicts",
            ],
            raw_output=json.dumps(parsed, indent=2)[:3000],
            processing_time_ms=elapsed,
        )

    def _summarize_docs(self, texts: List[str]) -> str:
        """Create a condensed summary of document claims."""
        parts = []
        for i, text in enumerate(texts[:5]):
            # Extract key sentences (those with dates, names, or evidence keywords)
            lines = text.split("\n")
            key_lines = [
                l.strip() for l in lines
                if len(l.strip()) > 30
                and any(k in l.lower() for k in [
                    "at ", "on ", "approximately", "witness", "victim", "suspect",
                    "evidence", "found", "observed", "stated", "confirmed",
                ])
            ]
            if key_lines:
                parts.append(f"[Document {i}]\n" + "\n".join(key_lines[:10]))
        return "\n\n".join(parts)

    def _summarize_videos(self, transcripts: List[Dict[str, Any]]) -> str:
        """Create a condensed summary of video evidence."""
        parts = []
        for vt in transcripts:
            idx = vt.get("video_index", 0)
            segments = vt.get("segments", [])
            if segments:
                seg_lines = [
                    f"  [{s['start']:.1f}s-{s['end']:.1f}s] {s['text']}"
                    for s in segments[:15]
                ]
                parts.append(f"[Video {idx}]\n" + "\n".join(seg_lines))
            elif vt.get("transcript"):
                parts.append(f"[Video {idx}] {vt['transcript'][:500]}")
        return "\n\n".join(parts)

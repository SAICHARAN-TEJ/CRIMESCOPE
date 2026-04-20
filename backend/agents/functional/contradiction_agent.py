# SPDX-License-Identifier: AGPL-3.0-only
"""
Contradiction Agent — cross-references evidence from multiple sources
to detect inconsistencies, fabrications, and temporal conflicts.

Responsibilities:
  - Compare document claims against video/audio evidence
  - Detect factual contradictions between witness statements
  - Identify temporal impossibilities (alibi conflicts)
  - Flag potential fabrication indicators
  - Score severity of each contradiction
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

logger = get_logger("crimescope.agent.contradiction")

CONTRADICTION_PROMPT = """You are a forensic contradiction analyst specializing in
detecting inconsistencies across multiple evidence sources.

DOCUMENT EVIDENCE:
{doc_evidence}

VIDEO/AUDIO EVIDENCE:
{av_evidence}

PREVIOUSLY EXTRACTED ENTITIES:
{entities_context}

Your task:
1. Cross-reference ALL claims from documents against video/audio evidence
2. Compare witness statements against each other
3. Check temporal consistency (can events have occurred in the stated order?)
4. Look for signs of fabrication or omission
5. Verify spatial consistency (locations, distances, travel times)

Return JSON:
{{
  "contradictions": [
    {{
      "type": "factual|temporal|spatial|witness_conflict|omission",
      "claim_a": "exact claim from source A",
      "source_a": "document_0|video_1|witness_statement",
      "claim_b": "conflicting claim from source B",
      "source_b": "document_1|video_0|witness_statement",
      "severity": 0.0-1.0,
      "explanation": "why these contradict",
      "forensic_significance": "high|medium|low",
      "possible_resolution": "how this might be explained"
    }}
  ],
  "fabrication_indicators": [
    {{
      "indicator": "what suggests fabrication",
      "source": "which source",
      "confidence": 0.0-1.0,
      "reasoning": "why this suggests fabrication"
    }}
  ],
  "verified_claims": [
    {{
      "claim": "claim that is corroborated by multiple sources",
      "sources": ["source_a", "source_b"],
      "confidence": 0.0-1.0
    }}
  ],
  "summary": "overall assessment of evidence consistency"
}}"""


class ContradictionAgent(FunctionalAgent):
    name = "contradiction_agent"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        start = time.time()

        doc_evidence = self._summarize_docs(input_data.raw_texts)
        av_evidence = self._summarize_av(input_data.video_transcripts)
        entities_ctx = self._format_entities(
            input_data.metadata.get("entities", [])
        )

        if not doc_evidence and not av_evidence:
            return self._empty_output("No evidence to cross-reference")

        try:
            prompt = CONTRADICTION_PROMPT.format(
                doc_evidence=doc_evidence[:3000],
                av_evidence=av_evidence[:2000],
                entities_context=entities_ctx[:1500],
            )
            raw = await openrouter.chat(
                settings.reasoning_model_name,
                prompt,
                system="You are a forensic contradiction analyst. Return only valid JSON.",
            )
            parsed = ModelRouter.parse_json_safe(raw)
        except Exception as e:
            logger.warning(f"Contradiction LLM call failed: {e}")
            parsed = None

        elapsed = (time.time() - start) * 1000

        if not parsed:
            return AgentOutput(
                agent_name=self.name,
                success=False,
                error="Contradiction analysis failed",
                processing_time_ms=elapsed,
            )

        contradictions = parsed.get("contradictions", [])
        fabrication_indicators = parsed.get("fabrication_indicators", [])
        verified = parsed.get("verified_claims", [])

        # Build graph relationships for contradictions
        relationships = []
        for c in contradictions:
            relationships.append({
                "source": c.get("source_a", "unknown"),
                "target": c.get("source_b", "unknown"),
                "type": "CONTRADICTS",
                "properties": {
                    "claim_a": c.get("claim_a", ""),
                    "claim_b": c.get("claim_b", ""),
                    "severity": c.get("severity", 0.5),
                    "contradiction_type": c.get("type", "factual"),
                },
            })

        for v in verified:
            for i in range(len(v.get("sources", [])) - 1):
                relationships.append({
                    "source": v["sources"][i],
                    "target": v["sources"][i + 1],
                    "type": "CORROBORATES",
                    "properties": {
                        "claim": v.get("claim", ""),
                        "confidence": v.get("confidence", 0.5),
                    },
                })

        facts = [
            f"Found {len(contradictions)} contradictions",
            f"Found {len(fabrication_indicators)} fabrication indicators",
            f"Verified {len(verified)} corroborated claims",
        ]

        # Categorise severity
        high_severity = [c for c in contradictions if c.get("severity", 0) >= 0.7]
        if high_severity:
            facts.append(f"⚠ {len(high_severity)} HIGH-SEVERITY contradictions detected")

        return AgentOutput(
            agent_name=self.name,
            success=True,
            contradictions=contradictions,
            relationships=relationships,
            facts=facts,
            raw_output=json.dumps(parsed, indent=2)[:3000],
            processing_time_ms=elapsed,
        )

    def _summarize_docs(self, texts: List[str]) -> str:
        """Extract claim-bearing sentences from documents."""
        parts = []
        claim_keywords = [
            "stated", "claimed", "reported", "observed", "testified",
            "confirmed", "denied", "alleged", "according to", "witness",
            "suspect", "victim", "evidence shows", "found", "located",
        ]
        for i, text in enumerate(texts[:5]):
            lines = text.split("\n")
            claim_lines = [
                l.strip() for l in lines
                if len(l.strip()) > 25
                and any(k in l.lower() for k in claim_keywords)
            ]
            if claim_lines:
                parts.append(f"[Document {i}]\n" + "\n".join(claim_lines[:12]))
            elif text.strip():
                parts.append(f"[Document {i}]\n" + "\n".join(lines[:5]))
        return "\n\n".join(parts)

    def _summarize_av(self, transcripts: List[Dict[str, Any]]) -> str:
        """Summarize audio/video evidence for cross-referencing."""
        parts = []
        for vt in transcripts:
            idx = vt.get("video_index", 0)
            segments = vt.get("segments", [])
            if segments:
                seg_lines = [
                    f"  [{s['start']:.1f}s-{s['end']:.1f}s] {s['text']}"
                    for s in segments[:20]
                ]
                parts.append(f"[Video {idx}]\n" + "\n".join(seg_lines))
            elif vt.get("transcript"):
                parts.append(f"[Video {idx}] {vt['transcript'][:500]}")
        return "\n\n".join(parts)

    def _format_entities(self, entities: List[Dict[str, Any]]) -> str:
        """Format previously-extracted entities for context."""
        if not entities:
            return "No entities previously extracted."
        lines = []
        for ent in entities[:20]:
            name = ent.get("name", "?")
            etype = ent.get("type", "unknown")
            desc = ent.get("description", "")
            lines.append(f"  - {name} ({etype}): {desc[:80]}")
        return "\n".join(lines)

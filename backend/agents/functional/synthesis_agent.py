# SPDX-License-Identifier: AGPL-3.0-only
"""
Synthesis Agent — final aggregation stage that merges ALL agent outputs
into a structured Probable Cause Report with ranked hypotheses.

This agent runs AFTER all parallel agents complete. It receives the
merged outputs and synthesizes a comprehensive investigative report.
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

logger = get_logger("crimescope.agent.synthesis")

SYNTHESIS_PROMPT = """You are the CrimeScope Lead Investigator synthesizing ALL evidence
into a final Probable Cause Report.

EXTRACTED ENTITIES ({entity_count}):
{entities_text}

TIMELINE ({timeline_count} events):
{timeline_text}

CONTRADICTIONS ({contradiction_count}):
{contradictions_text}

EVIDENCE CORRELATIONS:
{correlations_text}

LEGAL ANALYSIS:
{legal_text}

ALL FACTS:
{facts_text}

Generate a comprehensive Probable Cause Report:
1. EXECUTIVE SUMMARY: 2-3 paragraph overview of the case
2. KEY FINDINGS: Numbered list of the most significant findings
3. EVIDENCE CHAIN: How each piece of evidence connects
4. HYPOTHESES: Rank 3-5 hypotheses by probability
5. CONTRADICTIONS & RISKS: What weakens the case
6. RECOMMENDED ACTIONS: Next investigative steps
7. CONFIDENCE ASSESSMENT: Overall confidence in the analysis

Return JSON:
{{
  "executive_summary": "...",
  "key_findings": ["...", "..."],
  "evidence_chain": [
    {{"from": "...", "to": "...", "connection": "...", "strength": 0.0-1.0}}
  ],
  "hypotheses": [
    {{
      "rank": 1,
      "description": "...",
      "probability": 0.0-1.0,
      "supporting_evidence": ["..."],
      "weaknesses": ["..."]
    }}
  ],
  "contradictions_summary": "...",
  "recommended_actions": ["..."],
  "overall_confidence": 0.0-1.0,
  "report_quality_notes": "any limitations or caveats"
}}"""


class SynthesisAgent(FunctionalAgent):
    name = "synthesis_agent"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        start = time.time()

        # Extract aggregated data from metadata (populated by supervisor)
        meta = input_data.metadata
        entities = meta.get("all_entities", [])
        timeline = meta.get("all_timeline", [])
        contradictions = meta.get("all_contradictions", [])
        facts = meta.get("all_facts", [])
        legal = meta.get("all_legal", [])
        correlations = meta.get("correlations_text", "")

        if not entities and not timeline and not facts:
            return self._empty_output("No agent outputs to synthesize")

        try:
            prompt = SYNTHESIS_PROMPT.format(
                entity_count=len(entities),
                entities_text=self._format_entities(entities)[:2000],
                timeline_count=len(timeline),
                timeline_text=self._format_timeline(timeline)[:1500],
                contradiction_count=len(contradictions),
                contradictions_text=self._format_contradictions(contradictions)[:1500],
                correlations_text=str(correlations)[:1000],
                legal_text=self._format_legal(legal)[:1000],
                facts_text="\n".join(f"• {f}" for f in facts[:20]),
            )
            raw = await openrouter.chat(
                settings.synthesis_model_name,
                prompt,
                system=(
                    "You are the CrimeScope lead investigator. "
                    "Generate a complete, authoritative Probable Cause Report. "
                    "Return only valid JSON."
                ),
            )
            parsed = ModelRouter.parse_json_safe(raw)
        except Exception as e:
            logger.warning(f"Synthesis LLM call failed: {e}")
            parsed = None

        elapsed = (time.time() - start) * 1000

        if not parsed:
            return AgentOutput(
                agent_name=self.name,
                success=False,
                error="Report synthesis failed",
                processing_time_ms=elapsed,
            )

        # Build output
        hypotheses = parsed.get("hypotheses", [])
        report_facts = [
            f"Executive Summary: {parsed.get('executive_summary', '')[:200]}...",
            f"Generated {len(hypotheses)} ranked hypotheses",
            f"Overall confidence: {parsed.get('overall_confidence', 0):.0%}",
            f"Recommended {len(parsed.get('recommended_actions', []))} next actions",
        ]
        report_facts.extend(parsed.get("key_findings", [])[:5])

        # Build evidence chain as graph relationships
        relationships = []
        for link in parsed.get("evidence_chain", []):
            relationships.append({
                "source": link.get("from", ""),
                "target": link.get("to", ""),
                "type": "EVIDENCE_CHAIN",
                "properties": {
                    "connection": link.get("connection", ""),
                    "strength": link.get("strength", 0.5),
                },
            })

        return AgentOutput(
            agent_name=self.name,
            success=True,
            entities=[],  # Already extracted by upstream agents
            relationships=relationships,
            facts=report_facts,
            legal_findings=[{
                "type": "synthesis_report",
                "hypotheses": hypotheses,
                "executive_summary": parsed.get("executive_summary", ""),
                "recommended_actions": parsed.get("recommended_actions", []),
                "overall_confidence": parsed.get("overall_confidence", 0),
                "key_findings": parsed.get("key_findings", []),
            }],
            raw_output=json.dumps(parsed, indent=2)[:5000],
            processing_time_ms=elapsed,
        )

    def _format_entities(self, entities: List[Dict[str, Any]]) -> str:
        lines = []
        for ent in entities[:30]:
            name = ent.get("name", "?")
            etype = ent.get("type", "unknown")
            desc = ent.get("description", "")[:60]
            conf = ent.get("confidence", 0)
            lines.append(f"  [{etype}] {name}: {desc} (conf: {conf})")
        return "\n".join(lines)

    def _format_timeline(self, events: List[Dict[str, Any]]) -> str:
        lines = []
        for ev in events[:20]:
            t = ev.get("time", "?")
            desc = ev.get("event", ev.get("description", "?"))[:80]
            src = ev.get("source", "?")
            lines.append(f"  {t} — {desc} [src: {src}]")
        return "\n".join(lines)

    def _format_contradictions(self, contradictions: List[Dict[str, Any]]) -> str:
        lines = []
        for c in contradictions[:10]:
            ca = c.get("claim_a", c.get("event", "?"))[:50]
            cb = c.get("claim_b", c.get("conflict", "?"))[:50]
            sev = c.get("severity", "?")
            lines.append(f"  ⚠ {ca} vs. {cb} (severity: {sev})")
        return "\n".join(lines)

    def _format_legal(self, findings: List[Dict[str, Any]]) -> str:
        lines = []
        for f in findings[:10]:
            ftype = f.get("type", "finding")
            desc = str(f)[:100]
            lines.append(f"  [{ftype}] {desc}")
        return "\n".join(lines)

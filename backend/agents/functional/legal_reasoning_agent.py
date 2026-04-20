# SPDX-License-Identifier: AGPL-3.0-only
"""
Legal Reasoning Agent — applies rule-based logic and legal frameworks
to extracted evidence findings.

Capabilities:
  - Probable cause assessment
  - Statute/charge matching
  - Chain of custody validation
  - Admissibility screening
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

logger = get_logger("crimescope.agent.legal_reasoning")

LEGAL_PROMPT = """You are a senior legal analyst conducting a preliminary legal assessment.

EVIDENCE SUMMARY:
{evidence}

ENTITIES IDENTIFIED:
{entities}

CONTRADICTIONS FOUND:
{contradictions}

Perform the following analyses:
1. PROBABLE CAUSE ASSESSMENT: Is there probable cause for criminal charges?
2. POTENTIAL CHARGES: What charges could be filed based on evidence?
3. EVIDENCE STRENGTH: Rate the strength of each key piece of evidence
4. CHAIN OF CUSTODY: Flag any potential chain of custody issues
5. ADMISSIBILITY: Flag any evidence that may be inadmissible and why
6. DEFENSE VULNERABILITIES: Identify weak points a defense attorney would exploit

Return JSON:
{{
  "probable_cause": {{
    "exists": true/false,
    "confidence": 0.0-1.0,
    "summary": "..."
  }},
  "potential_charges": [
    {{"charge": "...", "statute": "...", "elements_met": ["..."], "elements_missing": ["..."], "likelihood": 0.0-1.0}}
  ],
  "evidence_strength": [
    {{"evidence": "...", "strength": "strong|moderate|weak", "reasoning": "..."}}
  ],
  "custody_issues": [
    {{"evidence": "...", "issue": "...", "severity": "high|medium|low"}}
  ],
  "admissibility_flags": [
    {{"evidence": "...", "concern": "...", "rule": "..."}}
  ],
  "defense_vulnerabilities": [
    {{"vulnerability": "...", "affected_evidence": "...", "risk": "high|medium|low"}}
  ]
}}"""


class LegalReasoningAgent(FunctionalAgent):
    name = "legal_reasoning_agent"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        start = time.time()

        evidence_summary = "\n".join(input_data.raw_texts[:3])[:3000] if input_data.raw_texts else "No documents"
        entities_str = json.dumps(input_data.metadata.get("entities", [])[:20], indent=1)[:2000]
        contradictions_str = json.dumps(input_data.metadata.get("contradictions", [])[:10], indent=1)[:1500]

        try:
            prompt = LEGAL_PROMPT.format(
                evidence=evidence_summary,
                entities=entities_str,
                contradictions=contradictions_str,
            )
            raw = await openrouter.chat(
                settings.reasoning_model_name,
                prompt,
                system="You are a senior prosecutorial analyst. Return only valid JSON.",
            )
            parsed = ModelRouter.parse_json_safe(raw)
        except Exception as e:
            logger.warning(f"Legal reasoning LLM call failed: {e}")
            parsed = None

        elapsed = (time.time() - start) * 1000

        if not parsed:
            return AgentOutput(
                agent_name=self.name,
                success=False,
                error="Legal analysis failed",
                processing_time_ms=elapsed,
            )

        # Build structured findings
        legal_findings = []
        pc = parsed.get("probable_cause", {})
        if pc:
            legal_findings.append({
                "type": "probable_cause",
                "exists": pc.get("exists", False),
                "confidence": pc.get("confidence", 0.0),
                "summary": pc.get("summary", ""),
            })

        for charge in parsed.get("potential_charges", []):
            legal_findings.append({
                "type": "potential_charge",
                **charge,
            })

        facts = []
        if pc.get("exists"):
            facts.append(f"Probable cause EXISTS (confidence: {pc.get('confidence', 0):.0%})")
        else:
            facts.append("Probable cause NOT established")

        charges = parsed.get("potential_charges", [])
        if charges:
            facts.append(f"{len(charges)} potential charges identified")

        vuln_count = len(parsed.get("defense_vulnerabilities", []))
        if vuln_count:
            facts.append(f"{vuln_count} defense vulnerabilities flagged")

        return AgentOutput(
            agent_name=self.name,
            success=True,
            legal_findings=legal_findings,
            facts=facts,
            contradictions=parsed.get("admissibility_flags", []),
            raw_output=json.dumps(parsed, indent=2)[:5000],
            processing_time_ms=elapsed,
        )

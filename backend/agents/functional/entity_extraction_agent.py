# SPDX-License-Identifier: AGPL-3.0-only
"""
Entity Extraction Agent — NER via LLM for criminal investigation entities.

Extracts: Person, Location, Date, Crime, Evidence, Vehicle, Weapon
from cleaned document text using structured JSON prompts.
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

logger = get_logger("crimescope.agent.entity_extraction")

EXTRACTION_PROMPT = """Extract ALL entities from the following evidence text.
Be exhaustive — identify every person, location, date/time, crime, evidence item,
vehicle, and weapon mentioned.

TEXT:
{text}

Return a JSON array of entities:
[
  {{
    "name": "exact name or identifier",
    "type": "person|location|date|crime|evidence|vehicle|weapon|organization",
    "description": "brief context from the text",
    "confidence": 0.0-1.0,
    "aliases": ["any alternative names"]
  }}
]

Rules:
- Include EVERY entity, even if mentioned once
- For persons, note their role if mentioned (victim, suspect, witness, officer)
- For dates/times, use ISO format where possible
- For evidence, note where/how it was found
- Confidence reflects how certain you are about the extraction"""


class EntityExtractionAgent(FunctionalAgent):
    name = "entity_extraction_agent"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        start = time.time()
        all_entities: List[Dict[str, Any]] = []
        all_timeline: List[Dict[str, Any]] = []

        # Process document texts
        for i, text in enumerate(input_data.raw_texts[:5]):
            entities = await self._extract_from_text(text[:6000], i)
            all_entities.extend(entities)

        # Process video transcripts
        for vt in input_data.video_transcripts:
            transcript = vt.get("transcript", "")
            if transcript and len(transcript) > 50:
                entities = await self._extract_from_text(
                    f"[Video transcript] {transcript[:4000]}", -1
                )
                # Add timestamp context from segments
                for seg in vt.get("segments", [])[:20]:
                    all_timeline.append({
                        "time": f"{seg['start']:.1f}s - {seg['end']:.1f}s",
                        "event": seg.get("text", ""),
                        "source": "video_audio",
                    })
                all_entities.extend(entities)

        # Deduplicate entities by name (case-insensitive)
        deduped = self._deduplicate(all_entities)

        # Extract timeline events from date/time entities
        for ent in deduped:
            if ent.get("type") == "date":
                all_timeline.append({
                    "time": ent.get("name", ""),
                    "event": ent.get("description", ""),
                    "source": "document",
                })

        elapsed = (time.time() - start) * 1000
        return AgentOutput(
            agent_name=self.name,
            success=True,
            entities=deduped,
            timeline_events=all_timeline,
            facts=[f"Extracted {len(deduped)} unique entities from {len(input_data.raw_texts)} sources"],
            processing_time_ms=elapsed,
        )

    async def _extract_from_text(self, text: str, doc_index: int) -> List[Dict[str, Any]]:
        """Extract entities from a single text via LLM."""
        try:
            prompt = EXTRACTION_PROMPT.format(text=text)
            raw = await openrouter.chat(
                settings.fast_model_name,
                prompt,
                system="You are a forensic NER engine. Return only valid JSON arrays.",
            )
            parsed = ModelRouter.parse_json_safe(raw)
            if isinstance(parsed, list):
                for ent in parsed:
                    ent["source_doc_index"] = doc_index
                return parsed
            elif isinstance(parsed, dict) and "entities" in parsed:
                for ent in parsed["entities"]:
                    ent["source_doc_index"] = doc_index
                return parsed["entities"]
        except Exception as e:
            logger.warning(f"Entity extraction failed for doc {doc_index}: {e}")
        return []

    def _deduplicate(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge duplicate entities by name, keeping highest confidence."""
        seen: Dict[str, Dict[str, Any]] = {}
        for ent in entities:
            key = ent.get("name", "").lower().strip()
            if not key:
                continue
            if key in seen:
                existing = seen[key]
                if float(ent.get("confidence", 0)) > float(existing.get("confidence", 0)):
                    seen[key] = ent
                # Merge aliases
                existing_aliases = set(existing.get("aliases", []))
                new_aliases = set(ent.get("aliases", []))
                seen[key]["aliases"] = list(existing_aliases | new_aliases)
            else:
                seen[key] = ent
        return list(seen.values())

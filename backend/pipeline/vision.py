# SPDX-License-Identifier: AGPL-3.0-only
"""
Mode 1 — Vision pipeline: analyse crime scene photographs.

Uses the vision model to extract forensic observations
from each image via multimodal API, then merges into a UnifiedSeedPacket.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List

from backend.config import settings
from backend.llm import ModelRouter
from backend.pipeline.schemas import (
    Entity,
    ForensicObservation,
    UnifiedSeedPacket,
)
from backend.utils.openrouter import openrouter
from backend.utils.logger import get_logger

logger = get_logger("crimescope.pipeline.vision")

VISION_SYSTEM = (
    "You are a CrimeScope forensic image analyst. Examine the crime scene "
    "photograph with extreme precision. Identify every visible object, person, "
    "spatial relationship, blood pattern, trace evidence, and anomaly. "
    "Return your analysis as JSON matching the ForensicObservation schema."
)

VISION_USER_TEMPLATE = """Analyse this crime scene photograph.
Context from investigator: {description}

Return JSON:
{{
  "image_index": {idx},
  "scene_description": "...",
  "objects_detected": ["..."],
  "spatial_relationships": ["..."],
  "anomalies": ["..."],
  "blood_patterns": ["..."],
  "trace_evidence": ["..."],
  "environmental_conditions": "...",
  "estimated_time_of_day": "..."
}}"""

MERGE_PROMPT = """You have {count} forensic observations from crime scene photographs.
Investigator context: {description}

OBSERVATIONS:
{observations_json}

Synthesise these into a unified seed packet. Extract all entities (persons,
locations, evidence items, events, vehicles) with confidence scores. Build
a preliminary timeline. Suggest 3 initial hypotheses.

Return JSON matching UnifiedSeedPacket schema:
{{
  "title": "...",
  "description": "...",
  "mode": 1,
  "entities": [...],
  "key_persons": [...],
  "timeline": {{"earliest": "...", "latest": "...", "key_timestamps": [...]}},
  "facts": [...],
  "forensic_observations": [...],
  "evidence_summary": "...",
  "initial_hypotheses": ["..."]
}}"""


async def analyse_images(
    image_bytes_list: List[bytes],
    description: str,
) -> Dict[str, Any]:
    """Process up to MAX_IMAGES_MODE1 photos through the vision pipeline."""
    images = image_bytes_list[: settings.max_images_mode1]
    observations: List[ForensicObservation] = []

    # Step 1: Per-image forensic analysis using MULTIMODAL vision API
    for idx, img_bytes in enumerate(images):
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        prompt = VISION_USER_TEMPLATE.format(description=description, idx=idx)

        # FIX: Use openrouter.vision() to actually send the image to the API
        # Previously used openrouter.chat() which is text-only — images were
        # base64-encoded but never sent (dead variable bug).
        try:
            raw = await openrouter.vision(
                settings.vision_model_name,
                [b64],
                VISION_SYSTEM + "\n\n" + prompt,
            )
        except Exception as e:
            # Fallback: try text-only chat if vision model doesn't support multimodal
            logger.warning(f"Vision API failed for image {idx}, falling back to text: {e}")
            raw = await openrouter.chat(
                settings.vision_model_name,
                f"[Image {idx} could not be processed visually. "
                f"Context: {description}. Provide a generic forensic observation template.]",
                system=VISION_SYSTEM,
            )

        parsed = ModelRouter.parse_json_safe(raw)
        if parsed:
            obs = ForensicObservation(**parsed)
            observations.append(obs)
            logger.info(f"Vision image {idx}: {len(obs.objects_detected)} objects detected")
        else:
            logger.warning(f"Vision image {idx}: failed to parse response")
            observations.append(ForensicObservation(image_index=idx, scene_description=raw[:500]))

    # Step 2: Merge observations into seed packet
    merge_prompt = MERGE_PROMPT.format(
        count=len(observations),
        description=description,
        observations_json=json.dumps([o.model_dump() for o in observations], indent=2)[:4000],
    )

    raw_merge = await openrouter.chat(
        settings.reasoning_model_name,
        merge_prompt,
        system="You are a senior CrimeScope investigator synthesising forensic evidence.",
    )

    parsed_merge = ModelRouter.parse_json_safe(raw_merge)
    if parsed_merge:
        seed = UnifiedSeedPacket(**parsed_merge)
        return seed.model_dump()

    # Fallback: minimal seed from raw observations
    return UnifiedSeedPacket(
        title=description[:80],
        description=description,
        mode=1,
        forensic_observations=observations,
        evidence_summary=raw_merge[:1000] if raw_merge else "Analysis incomplete",
    ).model_dump()

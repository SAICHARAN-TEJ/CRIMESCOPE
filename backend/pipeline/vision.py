"""Mode 1 — Crime-scene photo analysis via Gemini Vision."""

from __future__ import annotations

import base64
from typing import Any, Dict, List

from backend.config import settings
from backend.utils.openrouter import openrouter


async def analyse_images(
    images: List[bytes], case_description: str
) -> Dict[str, Any]:
    """
    Send up to MAX_IMAGES_MODE1 images to Gemini 2.5 Pro Vision
    and return a structured seed packet.
    """
    images = images[: settings.max_images_mode1]
    b64_images = [base64.b64encode(img).decode() for img in images]

    prompt = (
        f"CASE: {case_description}\n\n"
        "You are a forensic imagery analyst. For each image:\n"
        "1. Describe every visible detail.\n"
        "2. Identify physical evidence.\n"
        "3. Note spatial relationships.\n"
        "4. Flag anomalies.\n\n"
        "Return JSON: {observations: [...], inferred_facts: [...], open_questions: [...]}"
    )

    raw = await openrouter.vision(settings.vision_model_name, b64_images, prompt)

    return {
        "mode": 1,
        "raw_analysis": raw,
        "source_image_count": len(images),
    }

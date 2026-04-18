# SPDX-License-Identifier: AGPL-3.0-only
"""
Mode 2 — Document & Video pipeline: 3-pass extraction.

Pass 1 (DeepSeek V3):  OCR/text → StructuredExtract
Pass 2 (Llama 3.3):    Cross-reference → ContradictionReport
Pass 3 (Gemini 2.5):   Synthesise → UnifiedSeedPacket
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from backend.config import settings
from backend.llm import ModelRouter
from backend.pipeline.schemas import (
    ContradictionReport,
    StructuredExtract,
    UnifiedSeedPacket,
)
from backend.utils.openrouter import openrouter
from backend.utils.logger import get_logger

logger = get_logger("crimescope.pipeline.documents")

# ── Pass 1: Structured extraction ────────────────────────────────────────

PASS1_SYSTEM = (
    "You are a CrimeScope document analyst. Extract every entity, fact, "
    "timeline event, and key person from the provided document text. "
    "Be exhaustive — miss nothing."
)

PASS1_TEMPLATE = """DOCUMENT TEXT:
{doc_text}

Question from investigator: {question}

Extract and return JSON matching StructuredExtract:
{{
  "entities": [{{"name": "...", "type": "person|location|evidence|event|vehicle|weapon", "description": "...", "confidence": 0.0-1.0}}],
  "facts": ["..."],
  "timeline": [{{"time": "...", "event": "..."}}],
  "key_persons": [{{"name": "...", "role": "victim|suspect|witness|associate", "description": "...", "alibi": "...", "motive": "...", "opportunity": "..."}}],
  "raw_text_summary": "..."
}}"""

# ── Pass 2: Contradiction detection ──────────────────────────────────────

PASS2_SYSTEM = (
    "You are a CrimeScope contradiction analyst. Compare all extracted "
    "facts and timelines to find inconsistencies, conflicting claims, "
    "and reliability issues."
)

PASS2_TEMPLATE = """EXTRACTED DATA (from {count} documents):
{extracts_json}

Find contradictions between sources. Rate severity (0-1) and explain.
Return JSON matching ContradictionReport:
{{
  "contradictions": [{{"source_a": "...", "source_b": "...", "claim_a": "...", "claim_b": "...", "severity": 0.0-1.0, "explanation": "..."}}],
  "reliability_scores": {{"source_name": 0.0-1.0}},
  "summary": "..."
}}"""

# ── Pass 3: Final synthesis ──────────────────────────────────────────────

PASS3_SYSTEM = (
    "You are a senior CrimeScope investigator. Synthesise all extractions "
    "and contradictions into a unified seed packet for the 1,000-agent swarm."
)

PASS3_TEMPLATE = """STRUCTURED EXTRACTS:
{extracts_json}

CONTRADICTION REPORT:
{contradictions_json}

Question: {question}

Produce the final UnifiedSeedPacket as JSON:
{{
  "title": "...",
  "description": "...",
  "mode": 2,
  "entities": [...],
  "key_persons": [...],
  "timeline": {{"earliest": "...", "latest": "...", "key_timestamps": [...]}},
  "facts": [...],
  "contradictions": [...],
  "evidence_summary": "...",
  "initial_hypotheses": ["...", "...", "..."]
}}"""


async def analyse_documents(
    doc_bytes_list: List[bytes],
    video_bytes_list: List[bytes],
    question: str,
) -> Dict[str, Any]:
    """3-pass pipeline for document + video evidence."""

    # ── Extract text from documents ──────────────────────────────────
    doc_texts: List[str] = []
    for i, raw in enumerate(doc_bytes_list[: settings.max_documents_mode2]):
        text = _extract_text(raw, i)
        if text:
            doc_texts.append(text)

    # ── Extract keyframes from videos ────────────────────────────────
    for i, raw in enumerate(video_bytes_list[: settings.max_videos_mode2]):
        caption = _extract_video_keyframes(raw, i)
        if caption:
            doc_texts.append(f"[Video {i} keyframes]: {caption}")

    if not doc_texts:
        return UnifiedSeedPacket(title=question[:80], description=question, mode=2).model_dump()

    # ── Pass 1: Structured extraction (DeepSeek V3) ──────────────────
    extracts: List[StructuredExtract] = []
    for j, text in enumerate(doc_texts):
        prompt = PASS1_TEMPLATE.format(doc_text=text[:4000], question=question)
        raw = await openrouter.chat(settings.llm_model_name, prompt, system=PASS1_SYSTEM)
        parsed = ModelRouter.parse_json_safe(raw)
        if parsed:
            extracts.append(StructuredExtract(**parsed))
            logger.info(f"Pass 1 doc {j}: {len(parsed.get('entities', []))} entities")
        else:
            extracts.append(StructuredExtract(raw_text_summary=raw[:1000]))

    # ── Pass 2: Contradiction detection (Llama 3.3) ──────────────────
    extracts_json = json.dumps([e.model_dump() for e in extracts], indent=2)[:5000]
    pass2_prompt = PASS2_TEMPLATE.format(count=len(extracts), extracts_json=extracts_json)
    raw2 = await openrouter.chat(settings.fast_model_name, pass2_prompt, system=PASS2_SYSTEM)
    parsed2 = ModelRouter.parse_json_safe(raw2)
    contradictions = ContradictionReport(**(parsed2 or {}))
    logger.info(f"Pass 2: {len(contradictions.contradictions)} contradictions found")

    # ── Pass 3: Final synthesis (Gemini 2.5 Pro) ─────────────────────
    pass3_prompt = PASS3_TEMPLATE.format(
        extracts_json=extracts_json[:4000],
        contradictions_json=json.dumps(contradictions.model_dump(), indent=2)[:2000],
        question=question,
    )
    raw3 = await openrouter.chat(settings.vision_model_name, pass3_prompt, system=PASS3_SYSTEM)
    parsed3 = ModelRouter.parse_json_safe(raw3)
    if parsed3:
        seed = UnifiedSeedPacket(**parsed3)
        return seed.model_dump()

    # Fallback
    return UnifiedSeedPacket(
        title=question[:80],
        description=question,
        mode=2,
        evidence_summary=raw3[:1000] if raw3 else "Synthesis incomplete",
    ).model_dump()


# ── Helpers ──────────────────────────────────────────────────────────────

def _extract_text(raw_bytes: bytes, idx: int) -> str:
    """Extract text from PDF, DOCX, or plain text."""
    # Try PDF
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        if text.strip():
            return text[:8000]
    except Exception:
        pass

    # Try DOCX
    try:
        import io
        from docx import Document as DocxDocument
        doc = DocxDocument(io.BytesIO(raw_bytes))
        text = "\n".join(p.text for p in doc.paragraphs)
        if text.strip():
            return text[:8000]
    except Exception:
        pass

    # Fallback: decode as UTF-8
    try:
        return raw_bytes.decode("utf-8", errors="replace")[:8000]
    except Exception:
        return f"[Document {idx}: unable to extract text]"


def _extract_video_keyframes(raw_bytes: bytes, idx: int) -> str:
    """Extract keyframe descriptions from video (placeholder)."""
    try:
        import tempfile
        import os
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(raw_bytes)
            temp_path = f.name

        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(temp_path)
            duration = clip.duration
            # Extract 3 keyframes at 25%, 50%, 75%
            timestamps = [duration * p for p in [0.25, 0.5, 0.75]]
            descriptions = []
            for t in timestamps:
                descriptions.append(f"Frame at {t:.1f}s")
            clip.close()
            return f"Video duration: {duration:.1f}s. Keyframes: {', '.join(descriptions)}"
        finally:
            os.unlink(temp_path)
    except Exception as e:
        logger.warning(f"Video keyframe extraction failed for video {idx}: {e}")
        return f"[Video {idx}: keyframe extraction unavailable]"

"""Mode 2 — Document & video transcript analysis pipeline."""

from __future__ import annotations

from typing import Any, Dict, List

from backend.config import settings
from backend.utils.openrouter import openrouter


async def analyse_documents(
    docs: List[bytes],
    videos: List[bytes],
    question: str,
) -> Dict[str, Any]:
    """
    Three-pass pipeline:
      Pass 1 (DeepSeek V3): Extract structural facts from documents.
      Pass 2 (Llama 3.3):   Cross-reference for contradictions.
      Pass 3 (Gemini 2.5):  Unified synthesis.
    """
    doc_texts = [d.decode("utf-8", errors="replace")[:8000] for d in docs]
    combined = "\n---\n".join(doc_texts)

    # Pass 1 — structure extraction
    pass1 = await openrouter.chat(
        settings.llm_model_name,
        f"Extract all factual claims from these documents:\n{combined}",
        system="Return a numbered list of facts. Be exhaustive.",
    )

    # Pass 2 — contradiction detection
    pass2 = await openrouter.chat(
        settings.fast_model_name,
        f"Facts extracted:\n{pass1}\n\nFind contradictions and inconsistencies.",
        system="Return JSON: {contradictions: [...], consistent_facts: [...]}",
    )

    # Pass 3 — unified synthesis
    pass3 = await openrouter.chat(
        settings.vision_model_name,
        (
            f"QUESTION: {question}\n\n"
            f"FACTS:\n{pass1}\n\n"
            f"CONTRADICTIONS:\n{pass2}\n\n"
            "Synthesise into a unified seed packet for criminal reconstruction."
        ),
        system="Return JSON: {unified_facts: [...], disputes: [...], priority: '...'}",
    )

    return {
        "mode": 2,
        "pass1_facts": pass1,
        "pass2_contradictions": pass2,
        "pass3_synthesis": pass3,
        "doc_count": len(docs),
        "video_count": len(videos),
    }

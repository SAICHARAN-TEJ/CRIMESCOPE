# SPDX-License-Identifier: AGPL-3.0-only
"""
Ingestion Agent — pre-processes and normalises raw evidence.

Responsibilities:
  - Strip headers/footers from legal documents
  - Detect and normalise encoding issues
  - Identify document type (police report, witness statement, forensic)
  - Language detection
  - Clean OCR artefacts from video frames
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from backend.agents.functional.base import FunctionalAgent, AgentInput, AgentOutput
from backend.pipeline.chunking import chunk_legal_document
from backend.utils.logger import get_logger

logger = get_logger("crimescope.agent.ingestion")

# ── Legal boilerplate patterns to strip ──────────────────────────────────
BOILERPLATE_PATTERNS = [
    r"(?i)^page\s+\d+\s+of\s+\d+\s*$",
    r"(?i)^confidential\s*$",
    r"(?i)^draft\s*—?\s*not\s+for\s+distribution\s*$",
    r"(?i)^\s*\d+\s*$",  # Standalone page numbers
    r"(?i)^copyright\s+©.*$",
]
COMPILED_BOILERPLATE = [re.compile(p, re.MULTILINE) for p in BOILERPLATE_PATTERNS]


class IngestionAgent(FunctionalAgent):
    name = "ingestion_agent"

    async def process(self, input_data: AgentInput) -> AgentOutput:
        start = time.time()
        cleaned_texts: List[str] = []
        doc_types: List[Dict[str, Any]] = []

        for i, raw in enumerate(input_data.raw_texts):
            cleaned = self._clean_text(raw)
            doc_type = self._detect_document_type(cleaned)
            cleaned_texts.append(cleaned)
            doc_types.append({
                "index": i,
                "type": doc_type,
                "char_count": len(cleaned),
                "chunk_count": len(chunk_legal_document(cleaned, max_chunk_tokens=2000)),
            })
            logger.info(f"  Ingestion doc {i}: type={doc_type}, {len(cleaned)} chars")

        # Clean OCR texts
        for i, ocr in enumerate(input_data.ocr_texts):
            cleaned_ocr = self._clean_ocr(ocr)
            if cleaned_ocr.strip():
                cleaned_texts.append(cleaned_ocr)

        elapsed = (time.time() - start) * 1000

        return AgentOutput(
            agent_name=self.name,
            success=True,
            facts=[f"Processed {len(input_data.raw_texts)} documents, {len(input_data.ocr_texts)} OCR frames"],
            entities=[],  # Ingestion agent doesn't extract entities
            raw_output="\n---\n".join(cleaned_texts[:3])[:5000],
            processing_time_ms=elapsed,
        )

    def _clean_text(self, text: str) -> str:
        """Remove boilerplate, fix encoding, normalise whitespace."""
        for pattern in COMPILED_BOILERPLATE:
            text = pattern.sub("", text)

        # Fix common OCR/encoding issues
        text = text.replace("\x00", "")
        text = text.replace("\ufffd", "")
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{4,}", "\n\n\n", text)  # Collapse excessive newlines
        text = re.sub(r"[ \t]{4,}", "  ", text)    # Collapse excessive spaces

        return text.strip()

    def _clean_ocr(self, text: str) -> str:
        """Clean OCR artefacts from video frame text."""
        text = re.sub(r"[|]{2,}", "", text)       # Remove pipe artefacts
        text = re.sub(r"[_]{3,}", "", text)        # Remove underline artefacts
        text = re.sub(r"\b\w\b\s+\b\w\b", lambda m: m.group().replace(" ", ""), text)  # Join split chars
        return self._clean_text(text)

    def _detect_document_type(self, text: str) -> str:
        """Classify document type from content."""
        text_lower = text[:3000].lower()
        if any(k in text_lower for k in ["incident report", "police report", "case number", "badge"]):
            return "police_report"
        if any(k in text_lower for k in ["witness statement", "deposition", "sworn testimony"]):
            return "witness_statement"
        if any(k in text_lower for k in ["forensic", "autopsy", "toxicology", "dna analysis"]):
            return "forensic_report"
        if any(k in text_lower for k in ["transcript", "audio transcript", "video transcript"]):
            return "transcript"
        if any(k in text_lower for k in ["exhibit", "evidence log", "chain of custody"]):
            return "evidence_log"
        return "general_document"

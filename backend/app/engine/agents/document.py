"""
CrimeScope — Document Agent.

Parses PDF and DOCX files into structured text chunks.
Handles:
  - PDF extraction via pypdf
  - DOCX extraction via python-docx
  - Plain text fallback
  - Section-aware chunking for downstream NER
"""

from __future__ import annotations

import io
from typing import Any

from app.core.logger import get_logger
from app.engine.agents.base import BaseAgent
from app.schemas.events import AgentResult, AgentType
from app.storage.minio_client import get_minio

logger = get_logger("crimescope.agent.document")


def _parse_pdf(data: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except Exception as e:
        logger.warning(f"PDF parse failed: {e}")
        return ""


def _parse_docx(data: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.warning(f"DOCX parse failed: {e}")
        return ""


def _chunk_text(text: str, max_tokens: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for LLM context windows."""
    words = text.split()
    if len(words) <= max_tokens:
        return [text] if text.strip() else []
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + max_tokens])
        chunks.append(chunk)
        i += max_tokens - overlap
    return chunks


class DocumentAgent(BaseAgent):
    """
    Parses uploaded documents (PDF, DOCX, TXT) into text chunks.
    Downloads from MinIO, extracts content, and returns structured facts.
    """

    agent_type = AgentType.DOCUMENT
    agent_name = "document_agent"

    async def _execute(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        files = payload.get("files", [])
        doc_files = [
            f for f in files
            if not f.get("content_type", "").startswith("video/")
        ]

        if not doc_files:
            return AgentResult(
                agent=self.agent_type,
                success=True,
                facts=["No document files to process"],
            )

        minio = get_minio()
        all_chunks: list[str] = []
        all_facts: list[str] = []

        for df in doc_files:
            object_key = df["object_key"]
            filename = df.get("filename", "unknown")
            content_type = df.get("content_type", "")

            data = minio.get_object_bytes(object_key)
            if not data:
                all_facts.append(f"⚠ Could not download {filename}")
                continue

            # Parse based on content type
            if "pdf" in content_type or filename.lower().endswith(".pdf"):
                text = _parse_pdf(data)
            elif "docx" in content_type or filename.lower().endswith(".docx"):
                text = _parse_docx(data)
            else:
                text = data.decode("utf-8", errors="replace")

            if not text.strip():
                all_facts.append(f"⚠ No text extracted from {filename}")
                continue

            chunks = _chunk_text(text)
            all_chunks.extend(chunks)
            all_facts.append(
                f"Parsed {filename}: {len(text)} chars → {len(chunks)} chunks"
            )

        # Store chunks in payload for downstream agents
        payload["text_chunks"] = all_chunks

        return AgentResult(
            agent=self.agent_type,
            success=True,
            facts=all_facts,
        )

# SPDX-License-Identifier: AGPL-3.0-only
"""
Legal-context-aware document chunking strategies.

Optimised for criminal/legal documents where standard text splitting
destroys critical context (case numbers, section references, witness
statement boundaries).

Strategies:
  - Semantic: Split on legal section boundaries (headers, SECTION X, ARTICLE Y)
  - Preserving: Each chunk includes parent section header + document title
  - Overlapping: 15% overlap between chunks to prevent edge information loss
  - Size-bounded: Max 2000 tokens per chunk for optimal embedding quality
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Chunk:
    """A single chunk of document text with preserved context."""

    text: str
    index: int = 0
    section_header: str = ""
    document_title: str = ""
    page_number: Optional[int] = None
    char_start: int = 0
    char_end: int = 0

    @property
    def context_text(self) -> str:
        """Full text with preserved header/title context."""
        parts = []
        if self.document_title:
            parts.append(f"[Document: {self.document_title}]")
        if self.section_header:
            parts.append(f"[Section: {self.section_header}]")
        parts.append(self.text)
        return "\n".join(parts)

    def __len__(self) -> int:
        return len(self.text)


# ── Section boundary patterns ────────────────────────────────────────────

LEGAL_SECTION_PATTERNS = [
    # Explicit section headers
    r"^(?:SECTION|ARTICLE|CHAPTER|PART)\s+\d+",
    r"^(?:Section|Article|Chapter|Part)\s+\d+",
    # Numbered sections (1., 2., 1.1, etc.)
    r"^\d+\.\d*\s+[A-Z]",
    # Roman numeral sections
    r"^(?:I{1,4}|IV|V|VI{0,3}|IX|X)\.\s+",
    # Statement/deposition markers
    r"^(?:WITNESS STATEMENT|DEPOSITION|EXHIBIT|APPENDIX)",
    r"^(?:Witness Statement|Deposition|Exhibit|Appendix)",
    # Police report sections
    r"^(?:INCIDENT REPORT|NARRATIVE|EVIDENCE LOG|TIMELINE)",
    r"^(?:Incident Report|Narrative|Evidence Log|Timeline)",
    # All-caps lines (likely headers)
    r"^[A-Z][A-Z\s]{10,}$",
]

COMPILED_PATTERNS = [re.compile(p, re.MULTILINE) for p in LEGAL_SECTION_PATTERNS]


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // 4


def _find_section_boundaries(text: str) -> List[int]:
    """Find character positions where legal sections begin."""
    boundaries = set()
    for pattern in COMPILED_PATTERNS:
        for match in pattern.finditer(text):
            boundaries.add(match.start())
    return sorted(boundaries)


def chunk_legal_document(
    text: str,
    document_title: str = "",
    max_chunk_tokens: int = 2000,
    overlap_ratio: float = 0.15,
    min_chunk_tokens: int = 100,
) -> List[Chunk]:
    """
    Split a legal/criminal document into context-preserving chunks.

    Prioritises legal section boundaries for splitting, falls back to
    paragraph boundaries, then sentence boundaries.
    """
    if not text or not text.strip():
        return []

    max_chars = max_chunk_tokens * 4  # rough char limit
    overlap_chars = int(max_chars * overlap_ratio)
    min_chars = min_chunk_tokens * 4

    # Try section-boundary splitting first
    boundaries = _find_section_boundaries(text)

    if boundaries:
        chunks = _split_at_boundaries(text, boundaries, max_chars, overlap_chars)
    else:
        # Fallback: paragraph splitting
        chunks = _split_paragraphs(text, max_chars, overlap_chars)

    # Post-process: add context headers, merge tiny chunks
    result: List[Chunk] = []
    current_section = ""

    for i, raw_text in enumerate(chunks):
        raw_stripped = raw_text.strip()
        if not raw_stripped or _estimate_tokens(raw_stripped) < min_chunk_tokens:
            # Too small — merge with the previous chunk if possible
            if result:
                result[-1].text += "\n\n" + raw_stripped
                result[-1].char_end += len(raw_stripped) + 2
            continue

        # Detect section header from first line
        first_line = raw_stripped.split("\n")[0].strip()
        if any(p.match(first_line) for p in COMPILED_PATTERNS):
            current_section = first_line[:100]

        result.append(Chunk(
            text=raw_stripped,
            index=len(result),
            section_header=current_section,
            document_title=document_title,
        ))

    return result


def _split_at_boundaries(
    text: str, boundaries: List[int], max_chars: int, overlap_chars: int
) -> List[str]:
    """Split text at section boundaries, respecting max chunk size."""
    chunks: List[str] = []

    # Add text start and end as implicit boundaries
    all_bounds = [0] + boundaries + [len(text)]

    i = 0
    while i < len(all_bounds) - 1:
        start = all_bounds[i]
        # Find how far we can go without exceeding max_chars
        end = start
        j = i + 1
        while j < len(all_bounds) and all_bounds[j] - start <= max_chars:
            end = all_bounds[j]
            j += 1

        if end == start:
            # Single section exceeds max_chars — force split
            end = min(start + max_chars, len(text))
            j = i + 1

        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)

        # Apply overlap — start next chunk slightly before the boundary
        if overlap_chars > 0 and end < len(text):
            overlap_start = max(start, end - overlap_chars)
            # Find the actual boundary index for the overlap start
            next_i = j - 1
            while next_i > i and all_bounds[next_i] > overlap_start:
                next_i -= 1
            i = max(next_i, i + 1)
        else:
            i = j - 1
            if i <= (len(all_bounds) - 2) and all_bounds[i] <= start:
                i += 1

    return chunks


def _split_paragraphs(
    text: str, max_chars: int, overlap_chars: int
) -> List[str]:
    """Fallback: split on paragraph boundaries (\n\n)."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars:
            if current.strip():
                chunks.append(current.strip())
            # Start new chunk with overlap from previous
            if overlap_chars > 0 and current:
                current = current[-overlap_chars:] + "\n\n" + para
            else:
                current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks


def chunk_witness_statement(
    text: str,
    witness_name: str = "",
    max_chunk_tokens: int = 1500,
) -> List[Chunk]:
    """
    Specialised chunker for witness statements.

    Preserves Q&A pairs and deposition structure.
    """
    # Split on Q: / A: patterns
    qa_pattern = re.compile(r"(?:^|\n)([QA][:.])", re.MULTILINE)
    segments = qa_pattern.split(text)

    # Reconstitute Q&A pairs
    chunks: List[Chunk] = []
    current = ""
    max_chars = max_chunk_tokens * 4

    for seg in segments:
        if len(current) + len(seg) > max_chars and current.strip():
            chunks.append(Chunk(
                text=current.strip(),
                index=len(chunks),
                section_header=f"Witness: {witness_name}" if witness_name else "",
                document_title=f"Statement of {witness_name}" if witness_name else "",
            ))
            current = seg
        else:
            current += seg

    if current.strip():
        chunks.append(Chunk(
            text=current.strip(),
            index=len(chunks),
            section_header=f"Witness: {witness_name}" if witness_name else "",
            document_title=f"Statement of {witness_name}" if witness_name else "",
        ))

    return chunks

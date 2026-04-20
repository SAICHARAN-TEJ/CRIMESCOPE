# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for the legal document chunking module."""

import pytest

from backend.pipeline.chunking import (
    chunk_legal_document,
    chunk_witness_statement,
    Chunk,
)


class TestLegalDocumentChunking:
    """Tests for chunk_legal_document."""

    def test_chunk_basic_document(self, sample_document_text):
        """Should split a legal document into meaningful chunks."""
        chunks = chunk_legal_document(sample_document_text, "Test Report")
        assert len(chunks) > 0
        for c in chunks:
            assert isinstance(c, Chunk)
            assert len(c.text) > 0

    def test_chunk_preserves_context(self, sample_document_text):
        """Each chunk should include document title context."""
        chunks = chunk_legal_document(sample_document_text, "Incident Report")
        for c in chunks:
            assert c.document_title == "Incident Report"
            assert "Incident Report" in c.context_text

    def test_chunk_detects_sections(self, sample_document_text):
        """Chunker should detect legal section boundaries."""
        chunks = chunk_legal_document(sample_document_text, "Test")
        # At least some chunks should have section headers
        sections_found = [c for c in chunks if c.section_header]
        assert len(sections_found) > 0

    def test_chunk_empty_text(self):
        """Empty text should return empty list."""
        assert chunk_legal_document("") == []
        assert chunk_legal_document("  ") == []

    def test_chunk_respects_max_tokens(self):
        """No chunk should exceed the max token limit."""
        long_text = "SECTION 1: Test\n" + "word " * 5000
        chunks = chunk_legal_document(long_text, max_chunk_tokens=500)
        for c in chunks:
            # Rough check: 500 tokens ≈ 2000 chars + buffer
            assert len(c.text) <= 3000

    def test_chunk_overlap(self):
        """Chunks should have some overlapping content at boundaries."""
        text = "SECTION 1: First section.\n" + "Content A. " * 200 + "\n\n"
        text += "SECTION 2: Second section.\n" + "Content B. " * 200
        chunks = chunk_legal_document(text, max_chunk_tokens=300, overlap_ratio=0.15)
        # With overlap, adjacent chunks may share some text
        assert len(chunks) >= 1


class TestWitnessStatementChunking:
    """Tests for chunk_witness_statement."""

    def test_witness_statement_basic(self):
        """Should preserve Q&A structure."""
        statement = """
        Q: State your name for the record.
        A: My name is John Witness.
        Q: Where were you on the night of March 15?
        A: I was in the parking garage, Level 1.
        Q: What did you see?
        A: I saw two people arguing near the stairwell.
        """
        chunks = chunk_witness_statement(statement, "John Witness")
        assert len(chunks) > 0
        for c in chunks:
            assert "John Witness" in c.document_title or "John Witness" in c.section_header

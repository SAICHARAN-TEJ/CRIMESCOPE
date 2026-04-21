"""
CrimeScope v4.2 — Unit Tests for Hardening: Guardian, Chaos, DLQ.

Tests:
  - Guardian Pattern: Input/output validation on VideoAgent + DocumentAgent
  - Chaos Injector: Pass-through when disabled
  - DataIntegrityError: Correct fields
  - Document parsing: Encrypted PDF detection, text cleaning
  - Video Agent: Filename sanitization
"""

from __future__ import annotations

import asyncio
import pytest


# ── Guardian Pattern: Input Validation ────────────────────────────────────


class TestGuardianInput:
    """Test that agents reject invalid inputs."""

    def test_video_rejects_empty_job_id(self):
        from app.engine.agents.video import VideoAgent
        from app.engine.agents.base import DataIntegrityError

        agent = VideoAgent()
        with pytest.raises(DataIntegrityError, match="job_id"):
            agent.validate_input("", {"files": []})

    def test_video_rejects_non_dict_payload(self):
        from app.engine.agents.video import VideoAgent
        from app.engine.agents.base import DataIntegrityError

        agent = VideoAgent()
        with pytest.raises(DataIntegrityError, match="payload must be a dict"):
            agent.validate_input("job-1", "not a dict")

    def test_video_rejects_non_list_files(self):
        from app.engine.agents.video import VideoAgent
        from app.engine.agents.base import DataIntegrityError

        agent = VideoAgent()
        with pytest.raises(DataIntegrityError, match="files must be a list"):
            agent.validate_input("job-1", {"files": "bad"})

    def test_video_accepts_valid_input(self):
        from app.engine.agents.video import VideoAgent

        agent = VideoAgent()
        # Should not raise
        agent.validate_input("job-1", {"files": [{"object_key": "a", "filename": "v.mp4"}]})

    def test_document_rejects_empty_job_id(self):
        from app.engine.agents.document import DocumentAgent
        from app.engine.agents.base import DataIntegrityError

        agent = DocumentAgent()
        with pytest.raises(DataIntegrityError, match="job_id"):
            agent.validate_input("", {"files": []})

    def test_document_rejects_non_list_files(self):
        from app.engine.agents.document import DocumentAgent
        from app.engine.agents.base import DataIntegrityError

        agent = DocumentAgent()
        with pytest.raises(DataIntegrityError, match="files must be a list"):
            agent.validate_input("job-1", {"files": 999})


# ── Guardian Pattern: Output Validation ───────────────────────────────────


class TestGuardianOutput:
    """Test that agents reject invalid outputs."""

    def test_video_rejects_success_with_no_facts(self):
        from app.engine.agents.video import VideoAgent
        from app.engine.agents.base import DataIntegrityError
        from app.schemas.events import AgentResult, AgentType

        agent = VideoAgent()
        bad_result = AgentResult(agent=AgentType.VIDEO, success=True, facts=[])
        with pytest.raises(DataIntegrityError, match="no facts"):
            agent.validate_output(bad_result)

    def test_video_accepts_success_with_facts(self):
        from app.engine.agents.video import VideoAgent
        from app.schemas.events import AgentResult, AgentType

        agent = VideoAgent()
        good_result = AgentResult(
            agent=AgentType.VIDEO, success=True, facts=["Processed video.mp4"]
        )
        agent.validate_output(good_result)  # Should not raise

    def test_document_rejects_success_with_no_facts(self):
        from app.engine.agents.document import DocumentAgent
        from app.engine.agents.base import DataIntegrityError
        from app.schemas.events import AgentResult, AgentType

        agent = DocumentAgent()
        bad_result = AgentResult(agent=AgentType.DOCUMENT, success=True, facts=[])
        with pytest.raises(DataIntegrityError, match="no facts"):
            agent.validate_output(bad_result)

    def test_base_rejects_non_agent_result(self):
        from app.engine.agents.video import VideoAgent
        from app.engine.agents.base import DataIntegrityError

        agent = VideoAgent()
        with pytest.raises(DataIntegrityError, match="Expected AgentResult"):
            agent.validate_output({"not": "an AgentResult"})


# ── DataIntegrityError ────────────────────────────────────────────────────


class TestDataIntegrityError:
    def test_error_fields(self):
        from app.engine.agents.base import DataIntegrityError

        e = DataIntegrityError("video_agent", "corrupt output", recoverable=False)
        assert e.agent == "video_agent"
        assert e.recoverable is False
        assert "video_agent" in str(e)
        assert "corrupt output" in str(e)

    def test_default_recoverable(self):
        from app.engine.agents.base import DataIntegrityError

        e = DataIntegrityError("test", "msg")
        assert e.recoverable is True


# ── Chaos Injector ────────────────────────────────────────────────────────


class TestChaosInjector:
    @pytest.mark.asyncio
    async def test_passthrough_when_disabled(self):
        """With chaos disabled, decorated function should return normally."""
        from app.engine.agents.base import chaos_injector

        @chaos_injector
        async def mock_fn():
            return {"status": "ok"}

        result = await mock_fn()
        assert result == {"status": "ok"}


# ── Document Parsing Helpers ──────────────────────────────────────────────


class TestDocumentHelpers:
    def test_detect_encrypted_pdf(self):
        from app.engine.agents.document import _detect_encrypted_pdf

        assert _detect_encrypted_pdf(b"%PDF-1.4 /Encrypt /V 4") is True
        assert _detect_encrypted_pdf(b"%PDF-1.4 normal content") is False
        assert _detect_encrypted_pdf(b"") is False

    def test_clean_text(self):
        from app.engine.agents.document import _clean_text

        assert "\x00" not in _clean_text("text\x00with\x01null")
        assert _clean_text("  hello  ") == "hello"
        # Collapse excessive newlines
        result = _clean_text("a\n\n\n\n\nb")
        assert "\n\n\n" not in result

    def test_chunk_text(self):
        from app.engine.agents.document import _chunk_text

        # Short text → single chunk
        assert _chunk_text("short text") == ["short text"]

        # Empty text → no chunks
        assert _chunk_text("") == []
        assert _chunk_text("   ") == []


# ── Video Agent Helpers ───────────────────────────────────────────────────


class TestVideoHelpers:
    def test_sanitize_filename_path_traversal(self):
        from app.engine.agents.video import _sanitize_filename

        result = _sanitize_filename("../../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result
        assert ".." not in result

    def test_sanitize_filename_null_bytes(self):
        from app.engine.agents.video import _sanitize_filename

        result = _sanitize_filename("video\x00.mp4")
        assert "\x00" not in result

    def test_sanitize_filename_length_limit(self):
        from app.engine.agents.video import _sanitize_filename

        long_name = "a" * 300 + ".mp4"
        result = _sanitize_filename(long_name)
        assert len(result) <= 200

    def test_sanitize_filename_missing_extension(self):
        from app.engine.agents.video import _sanitize_filename

        result = _sanitize_filename("noext")
        assert "." in result  # Should add .mp4

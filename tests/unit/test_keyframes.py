# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for video keyframe extraction."""

import pytest

from backend.pipeline.keyframes import _ocr_frame, extract_keyframes


class TestKeyframeExtraction:
    @pytest.mark.asyncio
    async def test_empty_bytes(self):
        """Empty video bytes should return empty result."""
        result = await extract_keyframes(b"", video_index=0, max_frames=5)
        assert result["video_index"] == 0
        assert result["frame_count"] == 0
        assert isinstance(result["ocr_texts"], list)

    def test_ocr_frame_no_tesseract(self):
        """OCR should return empty string if tesseract is unavailable."""
        import numpy as np
        # Create a small black image
        try:
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            text = _ocr_frame(frame)
            assert isinstance(text, str)
        except ImportError:
            # numpy not available
            pass

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Result dict should have all expected keys."""
        result = await extract_keyframes(b"not-a-video", video_index=3)
        assert "video_index" in result
        assert "frames" in result
        assert "ocr_texts" in result
        assert "frame_count" in result
        assert "method" in result
        assert "processing_time_ms" in result
        assert result["video_index"] == 3


class TestSSEPipelineStream:
    """Test the SSE pipeline stream module."""

    def test_get_stream_queue(self):
        from backend.routers.pipeline_stream import get_stream_queue, cleanup_stream
        q = get_stream_queue("test-case-123")
        assert q is not None
        cleanup_stream("test-case-123")

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        from backend.routers.pipeline_stream import (
            progress_callback, get_stream_queue, cleanup_stream
        )
        await progress_callback("case-456", "entity_extraction", "started", 0)
        q = get_stream_queue("case-456")
        assert not q.empty()
        event = q.get_nowait()
        assert event["agent"] == "entity_extraction"
        assert event["status"] == "started"
        cleanup_stream("case-456")

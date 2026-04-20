# SPDX-License-Identifier: AGPL-3.0-only
"""
Audio extraction pipeline — Whisper-based transcription for video evidence.

Pipeline:
  1. Extract audio track from video using ffmpeg subprocess
  2. Transcribe via openai-whisper (local model — no API cost)
  3. Timestamp-align transcript segments for evidence correlation
  4. Return structured transcript with per-segment timestamps
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger("crimescope.pipeline.audio")

# Model will be loaded on first use
_WHISPER_MODEL = None
_WHISPER_AVAILABLE = False

try:
    import whisper  # type: ignore[import-untyped]
    _WHISPER_AVAILABLE = True
except ImportError:
    logger.info("openai-whisper not installed — audio transcription unavailable")


def _get_whisper_model():
    """Lazy-load the Whisper model (base — 74M params)."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None and _WHISPER_AVAILABLE:
        try:
            import whisper
            _WHISPER_MODEL = whisper.load_model("base")
            logger.info("Whisper 'base' model loaded successfully")
        except Exception as e:
            logger.warning(f"Whisper model load failed: {e}")
    return _WHISPER_MODEL


def extract_audio_from_video(video_bytes: bytes, suffix: str = ".mp4") -> Optional[str]:
    """
    Extract audio track from video bytes using ffmpeg.

    Returns path to a temporary WAV file, or None on failure.
    Caller is responsible for cleanup.
    """
    video_path = None
    audio_path = None
    try:
        # Write video to temp file
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as vf:
            vf.write(video_bytes)
            video_path = vf.name

        # Extract audio to WAV
        audio_path = video_path.replace(suffix, ".wav")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",          # no video
            "-acodec", "pcm_s16le",  # PCM 16-bit output
            "-ar", "16000",  # 16kHz sample rate (Whisper optimal)
            "-ac", "1",      # mono
            "-y",            # overwrite
            audio_path,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            logger.warning(f"ffmpeg extraction failed: {result.stderr[:500]}")
            return None

        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            return audio_path
        return None

    except FileNotFoundError:
        logger.warning("ffmpeg not found in PATH — audio extraction unavailable")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg timed out after 120s")
        return None
    except Exception as e:
        logger.warning(f"Audio extraction error: {e}")
        return None
    finally:
        # Clean up video temp file (keep audio — caller cleans it)
        if video_path and os.path.exists(video_path):
            os.unlink(video_path)


def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """
    Transcribe audio file using Whisper.

    Returns:
        {
            "text": "full transcript...",
            "segments": [
                {"start": 0.0, "end": 3.5, "text": "segment text"},
                ...
            ],
            "language": "en",
            "duration": 120.5
        }
    """
    model = _get_whisper_model()
    if model is None:
        return {
            "text": "[Audio transcription unavailable — Whisper not installed]",
            "segments": [],
            "language": "unknown",
            "duration": 0.0,
        }

    try:
        result = model.transcribe(
            audio_path,
            fp16=False,  # CPU-safe
            language=None,  # auto-detect
            verbose=False,
        )
        segments = [
            {
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            }
            for seg in result.get("segments", [])
            if seg.get("text", "").strip()
        ]
        return {
            "text": result.get("text", "").strip(),
            "segments": segments,
            "language": result.get("language", "unknown"),
            "duration": segments[-1]["end"] if segments else 0.0,
        }
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return {
            "text": f"[Transcription failed: {str(e)[:200]}]",
            "segments": [],
            "language": "unknown",
            "duration": 0.0,
        }


async def process_video_audio(
    video_bytes: bytes,
    video_index: int = 0,
    suffix: str = ".mp4",
) -> Dict[str, Any]:
    """
    Full video audio pipeline — extract + transcribe.

    Returns structured transcript with timestamps suitable for
    evidence correlation with document claims.
    """
    logger.info(f"Processing audio for video {video_index} ({len(video_bytes)} bytes)")

    audio_path = extract_audio_from_video(video_bytes, suffix)
    if audio_path is None:
        return {
            "video_index": video_index,
            "transcript": "[Audio extraction failed]",
            "segments": [],
            "language": "unknown",
            "duration": 0.0,
        }

    try:
        result = transcribe_audio(audio_path)
        return {
            "video_index": video_index,
            "transcript": result["text"],
            "segments": result["segments"],
            "language": result["language"],
            "duration": result["duration"],
        }
    finally:
        # Clean up audio temp file
        if os.path.exists(audio_path):
            os.unlink(audio_path)

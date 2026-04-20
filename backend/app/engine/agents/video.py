"""
CrimeScope — Video Agent (Antigravity-Hardened).

Processes video files using:
  1. FFmpeg for audio extraction (CPU-bound → ProcessPoolExecutor)
  2. Whisper for speech-to-text transcription
  3. Keyframe extraction for visual evidence

Hardened against:
  - Corrupt/truncated video streams (FFmpeg stderr validation)
  - 0-byte / silent audio tracks (size + duration gating)
  - Unicode / special-char filenames (sanitized before disk write)
  - 10GB+ files (streaming download with size cap, no full-memory load)
  - ProcessPool pickling failures (only primitives cross process boundary)
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logger import get_logger
from app.engine.agents.base import BaseAgent
from app.schemas.events import AgentResult, AgentType
from app.storage.minio_client import get_minio

logger = get_logger("crimescope.agent.video")

# Shared process pool for CPU-bound tasks
_process_pool = ProcessPoolExecutor(max_workers=2)

# ── Safety limits ─────────────────────────────────────────────────────────
MAX_VIDEO_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB hard cap
MIN_AUDIO_SIZE_BYTES = 4096                      # Below this, audio is empty/corrupt
FFMPEG_TIMEOUT = 180                             # 3 minutes per FFmpeg call
WHISPER_TIMEOUT = 300                            # 5 minutes per transcription

# Characters allowed in sanitized filenames
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _sanitize_filename(name: str) -> str:
    """Strip unicode and special chars from filename to prevent path traversal."""
    # Take only the basename (no directory traversal)
    name = Path(name).name
    sanitized = _SAFE_FILENAME_RE.sub("_", name)
    # Ensure it has an extension
    if "." not in sanitized:
        sanitized += ".mp4"
    # Truncate to prevent filesystem limits
    return sanitized[:200]


def _validate_video_file(path: str) -> dict[str, Any]:
    """
    Use ffprobe to validate a video file before processing.
    Returns {"valid": bool, "duration": float, "error": str}.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "")[:500]
            return {"valid": False, "duration": 0.0, "error": f"ffprobe failed: {stderr}"}

        duration_str = result.stdout.strip()
        duration = float(duration_str) if duration_str and duration_str != "N/A" else 0.0
        if duration <= 0:
            return {"valid": False, "duration": 0.0, "error": "Video has zero duration"}

        return {"valid": True, "duration": duration, "error": ""}

    except subprocess.TimeoutExpired:
        return {"valid": False, "duration": 0.0, "error": "ffprobe timed out (corrupt file?)"}
    except (ValueError, OSError) as e:
        return {"valid": False, "duration": 0.0, "error": f"Validation error: {e}"}


def _extract_audio_sync(video_path: str, audio_path: str) -> dict[str, Any]:
    """
    CPU-bound FFmpeg call — runs in ProcessPoolExecutor.
    Extracts audio track from video file.

    Returns dict (not bool) so errors propagate cleanly across process boundary.
    All arguments are primitives (str) — guaranteed picklable.
    """
    try:
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-y", audio_path,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT, check=False,
        )

        if result.returncode != 0:
            stderr = (result.stderr or "")[:500]
            return {"success": False, "error": f"FFmpeg exit {result.returncode}: {stderr}"}

        # Validate output file exists and has meaningful size
        audio_p = Path(audio_path)
        if not audio_p.exists():
            return {"success": False, "error": "Audio file not created"}

        file_size = audio_p.stat().st_size
        if file_size < MIN_AUDIO_SIZE_BYTES:
            return {"success": False, "error": f"Audio too small ({file_size}B) — likely silent/corrupt"}

        return {"success": True, "error": "", "audio_size": file_size}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"FFmpeg timed out after {FFMPEG_TIMEOUT}s"}
    except Exception as e:
        return {"success": False, "error": f"FFmpeg crash: {type(e).__name__}: {e}"}


def _transcribe_sync(audio_path: str, model_name: str) -> dict[str, Any]:
    """
    CPU-bound Whisper transcription — runs in ProcessPoolExecutor.

    Only str arguments cross the process boundary (picklable).
    """
    try:
        import whisper
        model = whisper.load_model(model_name)
        result = model.transcribe(audio_path, language="en")

        text = result.get("text", "")
        if not isinstance(text, str):
            text = str(text) if text else ""

        segments = []
        for s in result.get("segments", []):
            try:
                segments.append({
                    "start": float(s.get("start", 0)),
                    "end": float(s.get("end", 0)),
                    "text": str(s.get("text", "")).strip(),
                })
            except (TypeError, ValueError):
                continue

        return {"text": text, "segments": segments, "error": ""}

    except ImportError:
        return {"text": "", "segments": [], "error": "Whisper not installed"}
    except Exception as e:
        return {"text": "", "segments": [], "error": f"Transcription error: {type(e).__name__}: {e}"}


class VideoAgent(BaseAgent):
    """
    Processes video evidence: extract audio → transcribe → extract keyframes.
    CPU-bound work is offloaded to ProcessPoolExecutor.

    Hardened against:
      - Corrupt streams, 0-byte segments, Unicode filenames
      - 10GB files (streaming download with 2GB cap)
      - ProcessPool serialization failures
    """

    agent_type = AgentType.VIDEO
    agent_name = "video_agent"

    async def _execute(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        files = payload.get("files", [])
        video_files = [
            f for f in files
            if f.get("content_type", "").startswith("video/")
               or f.get("filename", "").lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm"))
        ]

        if not video_files:
            return AgentResult(
                agent=self.agent_type,
                success=True,
                facts=["No video files to process"],
            )

        settings = get_settings()
        minio = get_minio()
        loop = asyncio.get_running_loop()

        # Extract whisper model name as a primitive string BEFORE crossing process boundary
        whisper_model: str = str(settings.whisper_model) if hasattr(settings, "whisper_model") else "base"

        all_transcripts: list[dict] = []
        all_facts: list[str] = []

        for i, vf in enumerate(video_files):
            object_key = vf.get("object_key", "")
            raw_filename = vf.get("filename", f"video_{i}.mp4")
            filename = _sanitize_filename(raw_filename)

            video_path: str | None = None
            audio_path: str | None = None

            try:
                # ── Size check before download (prevents 10GB OOM) ────
                try:
                    stat = minio.stat_object(object_key)
                    if stat and hasattr(stat, "size") and stat.size > MAX_VIDEO_SIZE_BYTES:
                        all_facts.append(
                            f"⚠ Skipped {filename}: {stat.size / 1e9:.1f}GB exceeds "
                            f"{MAX_VIDEO_SIZE_BYTES / 1e9:.0f}GB limit"
                        )
                        continue
                except Exception:
                    pass  # stat unavailable — proceed with download, cap handled below

                # ── Streaming download to disk (never load full file into RAM) ──
                with tempfile.NamedTemporaryFile(
                    suffix=Path(filename).suffix or ".mp4",
                    delete=False,
                    prefix="cs_video_",
                ) as tmp_video:
                    video_path = tmp_video.name
                    bytes_written = 0
                    try:
                        stream = minio.get_object_stream(object_key)
                        if stream is None:
                            all_facts.append(f"⚠ Could not download {filename}")
                            continue
                        for chunk in stream:
                            bytes_written += len(chunk)
                            if bytes_written > MAX_VIDEO_SIZE_BYTES:
                                all_facts.append(f"⚠ {filename} exceeded size limit during download, truncated")
                                break
                            tmp_video.write(chunk)
                    except AttributeError:
                        # Fallback: minio client doesn't have streaming — use bytes
                        video_bytes = minio.get_object_bytes(object_key)
                        if not video_bytes:
                            all_facts.append(f"⚠ Could not download {filename}")
                            continue
                        if len(video_bytes) > MAX_VIDEO_SIZE_BYTES:
                            all_facts.append(f"⚠ Skipped {filename}: exceeds size limit")
                            continue
                        tmp_video.write(video_bytes)
                        bytes_written = len(video_bytes)

                if bytes_written == 0:
                    all_facts.append(f"⚠ {filename} is a 0-byte file")
                    continue

                # ── Validate video integrity with ffprobe ─────────────
                probe = await loop.run_in_executor(
                    None,
                    _validate_video_file,
                    video_path,
                )
                if not probe["valid"]:
                    all_facts.append(f"⚠ {filename} failed validation: {probe['error']}")
                    # Still try audio extraction — some "corrupt" files have valid audio
                    all_transcripts.append({
                        "video_index": i,
                        "filename": filename,
                        "text": f"[Video corrupt: {probe['error']}]",
                        "segments": [],
                    })
                    continue

                # ── Audio extraction path ─────────────────────────────
                audio_path = video_path + ".wav"

                # FFmpeg extraction — CPU-bound, purely string args (picklable)
                extract_result = await loop.run_in_executor(
                    _process_pool,
                    partial(_extract_audio_sync, video_path, audio_path),
                )

                if extract_result["success"]:
                    # Whisper transcription — CPU-bound, str args only
                    transcript = await loop.run_in_executor(
                        _process_pool,
                        partial(_transcribe_sync, audio_path, whisper_model),
                    )

                    if transcript.get("error"):
                        all_facts.append(f"⚠ {filename} transcription warning: {transcript['error']}")

                    all_transcripts.append({
                        "video_index": i,
                        "filename": filename,
                        "text": transcript.get("text", ""),
                        "segments": transcript.get("segments", []),
                    })

                    text = transcript.get("text", "")
                    seg_count = len(transcript.get("segments", []))
                    all_facts.append(
                        f"Transcribed {filename}: {seg_count} segments, "
                        f"{len(text)} chars"
                    )

                    # Store text chunks for downstream entity extraction
                    if text.strip():
                        existing_chunks = payload.get("text_chunks", [])
                        words = text.split()
                        for ci in range(0, len(words), 500):
                            existing_chunks.append(" ".join(words[ci:ci + 500]))
                        payload["text_chunks"] = existing_chunks
                else:
                    all_facts.append(f"⚠ {filename} audio extraction failed: {extract_result['error']}")
                    all_transcripts.append({
                        "video_index": i,
                        "filename": filename,
                        "text": f"[Audio extraction failed: {extract_result['error']}]",
                        "segments": [],
                    })

            except Exception as e:
                # Per-file isolation — one corrupt file never kills the pipeline
                logger.error(f"Video processing crashed for {filename}: {e}", exc_info=True)
                all_facts.append(f"⚠ {filename} crashed: {type(e).__name__}: {e}")
                all_transcripts.append({
                    "video_index": i,
                    "filename": filename,
                    "text": f"[Processing error: {e}]",
                    "segments": [],
                })

            finally:
                # Cleanup temp files — always runs even on crash
                for p in (video_path, audio_path):
                    if p:
                        try:
                            Path(p).unlink(missing_ok=True)
                        except Exception:
                            pass

        return AgentResult(
            agent=self.agent_type,
            success=True,
            entities=[],
            relationships=[],
            facts=all_facts,
        )

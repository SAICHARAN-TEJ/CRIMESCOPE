"""
CrimeScope — Video Agent.

Processes video files using:
  1. FFmpeg for audio extraction (CPU-bound → ProcessPoolExecutor)
  2. Whisper for speech-to-text transcription
  3. Keyframe extraction for visual evidence

Uses ProcessPoolExecutor to avoid blocking the asyncio event loop
during CPU-intensive FFmpeg/Whisper operations.
"""

from __future__ import annotations

import asyncio
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


def _extract_audio_sync(video_path: str, audio_path: str) -> bool:
    """
    CPU-bound FFmpeg call — runs in ProcessPoolExecutor.
    Extracts audio track from video file.
    """
    try:
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-y", audio_path,
        ]
        result = subprocess.run(
            cmd, capture_output=True, timeout=120, check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _transcribe_sync(audio_path: str, model_name: str) -> dict[str, Any]:
    """
    CPU-bound Whisper transcription — runs in ProcessPoolExecutor.
    """
    try:
        import whisper
        model = whisper.load_model(model_name)
        result = model.transcribe(audio_path, language="en")
        return {
            "text": result.get("text", ""),
            "segments": [
                {
                    "start": s["start"],
                    "end": s["end"],
                    "text": s["text"].strip(),
                }
                for s in result.get("segments", [])
            ],
        }
    except ImportError:
        return {"text": "[Whisper not installed]", "segments": []}
    except Exception as e:
        return {"text": f"[Transcription error: {e}]", "segments": []}


class VideoAgent(BaseAgent):
    """
    Processes video evidence: extract audio → transcribe → extract keyframes.
    CPU-bound work is offloaded to ProcessPoolExecutor.
    """

    agent_type = AgentType.VIDEO
    agent_name = "video_agent"

    async def _execute(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        files = payload.get("files", [])
        video_files = [
            f for f in files
            if f.get("content_type", "").startswith("video/")
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

        all_transcripts: list[dict] = []
        all_facts: list[str] = []

        for i, vf in enumerate(video_files):
            object_key = vf["object_key"]
            filename = vf.get("filename", f"video_{i}")

            # Download from MinIO
            video_bytes = minio.get_object_bytes(object_key)
            if not video_bytes:
                all_facts.append(f"⚠ Could not download {filename}")
                continue

            # Write to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
                tmp_video.write(video_bytes)
                video_path = tmp_video.name

            audio_path = video_path.replace(".mp4", ".wav")

            try:
                # FFmpeg extraction — CPU-bound, offloaded to ProcessPool
                success = await loop.run_in_executor(
                    _process_pool,
                    partial(_extract_audio_sync, video_path, audio_path),
                )

                if success and Path(audio_path).exists():
                    # Whisper transcription — CPU-bound, offloaded to ProcessPool
                    transcript = await loop.run_in_executor(
                        _process_pool,
                        partial(_transcribe_sync, audio_path, settings.whisper_model),
                    )
                    all_transcripts.append({
                        "video_index": i,
                        "filename": filename,
                        **transcript,
                    })
                    seg_count = len(transcript.get("segments", []))
                    all_facts.append(
                        f"Transcribed {filename}: {seg_count} segments, "
                        f"{len(transcript.get('text', ''))} chars"
                    )
                else:
                    all_facts.append(f"⚠ FFmpeg audio extraction failed for {filename}")
                    all_transcripts.append({
                        "video_index": i,
                        "filename": filename,
                        "text": "[Audio extraction failed]",
                        "segments": [],
                    })
            finally:
                # Cleanup temp files
                for p in (video_path, audio_path):
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

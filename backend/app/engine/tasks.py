"""
CrimeScope — Celery Tasks for CPU-Heavy Processing.

Replaces ProcessPoolExecutor with proper distributed task queue.
Tasks are idempotent, retriable, and publish progress via Redis pub/sub.

Tasks:
  - process_video: FFmpeg keyframe extraction + Whisper transcription
  - process_document: PDF/DOCX text extraction with chunking
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import redis

from celery_config import app

# ── Redis client for event publishing (sync, used inside Celery workers) ──

_redis: redis.Redis | None = None


def _get_sync_redis() -> redis.Redis:
    """Get a synchronous Redis client for Celery workers."""
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    return _redis


def _publish_event(job_id: str, event: dict[str, Any]) -> None:
    """Publish an event to Redis pub/sub (sync version for workers)."""
    try:
        r = _get_sync_redis()
        r.publish(f"crimescope:{job_id}", json.dumps(event))
    except Exception:
        pass  # Non-critical — don't crash the task


def _push_to_graph_stream(items: list[dict[str, Any]]) -> None:
    """Push node/edge dicts to the Redis Stream `graph_writes` for write-behind."""
    try:
        r = _get_sync_redis()
        for item in items:
            r.xadd("graph_writes", {"data": json.dumps(item)}, maxlen=10000)
    except Exception:
        pass


# ── Video Processing Task ─────────────────────────────────────────────────


@app.task(
    bind=True,
    name="app.engine.tasks.process_video",
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=300,        # Hard kill after 5 min
    soft_time_limit=240,   # Graceful timeout at 4 min
)
def process_video(self, job_id: str, file_meta: dict[str, Any]) -> dict[str, Any]:
    """
    Process a video file: extract keyframes + transcribe audio.

    Args:
        job_id: Pipeline job ID for event correlation.
        file_meta: {object_key, filename, content_type}

    Returns:
        {text_chunks: [...], keyframes: [...], processing_time_ms: float}
    """
    start = time.time()
    filename = file_meta.get("filename", "unknown.mp4")
    object_key = file_meta.get("object_key", "")

    _publish_event(job_id, {
        "event": "AGENT_START",
        "job_id": job_id,
        "agent": "video",
        "data": {"filename": filename},
    })

    text_chunks: list[str] = []
    keyframes: list[str] = []

    try:
        # Download from MinIO (sync)
        from minio import Minio

        minio_client = Minio(
            os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "crimescope"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "crimescope-secret"),
            secure=False,
        )
        bucket = os.getenv("MINIO_BUCKET", "crimescope-uploads")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / filename
            minio_client.fget_object(bucket, object_key, str(local_path))

            # ── Extract keyframes with FFmpeg ─────────────────────────
            keyframe_dir = Path(tmpdir) / "keyframes"
            keyframe_dir.mkdir()

            subprocess.run(
                [
                    "ffmpeg", "-i", str(local_path),
                    "-vf", "select=eq(pict_type\\,I)",
                    "-vsync", "vfr",
                    "-frames:v", "20",
                    str(keyframe_dir / "frame_%04d.jpg"),
                ],
                capture_output=True, timeout=120, check=False,
            )
            keyframes = [f.name for f in sorted(keyframe_dir.glob("*.jpg"))]

            # ── Extract audio + transcribe ────────────────────────────
            audio_path = Path(tmpdir) / "audio.wav"
            subprocess.run(
                [
                    "ffmpeg", "-i", str(local_path),
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "16000", "-ac", "1",
                    str(audio_path),
                ],
                capture_output=True, timeout=120, check=False,
            )

            if audio_path.exists() and audio_path.stat().st_size > 1000:
                try:
                    import whisper
                    model = whisper.load_model("base")
                    result = model.transcribe(str(audio_path))
                    transcript = result.get("text", "")
                    if transcript.strip():
                        # Chunk transcript into ~500-word segments
                        words = transcript.split()
                        for i in range(0, len(words), 500):
                            chunk = " ".join(words[i:i + 500])
                            text_chunks.append(chunk)
                except ImportError:
                    text_chunks.append(f"[Whisper unavailable] Video processed: {filename}")

        elapsed = (time.time() - start) * 1000

        _publish_event(job_id, {
            "event": "AGENT_COMPLETE",
            "job_id": job_id,
            "agent": "video",
            "data": {
                "processing_time_ms": elapsed,
                "keyframes": len(keyframes),
                "chunks": len(text_chunks),
            },
        })

        return {
            "text_chunks": text_chunks,
            "keyframes": keyframes,
            "processing_time_ms": elapsed,
        }

    except Exception as exc:
        elapsed = (time.time() - start) * 1000
        _publish_event(job_id, {
            "event": "AGENT_ERROR",
            "job_id": job_id,
            "agent": "video",
            "data": {"error": str(exc), "processing_time_ms": elapsed},
        })
        raise self.retry(exc=exc)


# ── Document Processing Task ──────────────────────────────────────────────


@app.task(
    bind=True,
    name="app.engine.tasks.process_document",
    max_retries=2,
    default_retry_delay=5,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=120,
    soft_time_limit=100,
)
def process_document(self, job_id: str, file_meta: dict[str, Any]) -> dict[str, Any]:
    """
    Process a document: extract text and chunk it.

    Supports: PDF, DOCX, TXT.

    Args:
        job_id: Pipeline job ID.
        file_meta: {object_key, filename, content_type}

    Returns:
        {text_chunks: [...], processing_time_ms: float}
    """
    start = time.time()
    filename = file_meta.get("filename", "unknown")
    object_key = file_meta.get("object_key", "")
    content_type = file_meta.get("content_type", "")

    _publish_event(job_id, {
        "event": "AGENT_START",
        "job_id": job_id,
        "agent": "document",
        "data": {"filename": filename},
    })

    text_chunks: list[str] = []

    try:
        from minio import Minio

        minio_client = Minio(
            os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "crimescope"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "crimescope-secret"),
            secure=False,
        )
        bucket = os.getenv("MINIO_BUCKET", "crimescope-uploads")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / filename
            minio_client.fget_object(bucket, object_key, str(local_path))

            raw_text = ""

            # ── PDF extraction ────────────────────────────────────────
            if content_type == "application/pdf" or filename.endswith(".pdf"):
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(str(local_path))
                    pages = []
                    for page in doc:
                        pages.append(page.get_text())
                    raw_text = "\n\n".join(pages)
                    doc.close()
                except ImportError:
                    raw_text = local_path.read_text(errors="ignore")

            # ── DOCX extraction ───────────────────────────────────────
            elif filename.endswith(".docx"):
                try:
                    from docx import Document
                    doc = Document(str(local_path))
                    raw_text = "\n".join(p.text for p in doc.paragraphs)
                except ImportError:
                    raw_text = local_path.read_text(errors="ignore")

            # ── Plain text ────────────────────────────────────────────
            else:
                raw_text = local_path.read_text(errors="ignore")

            # ── Chunk with overlap ────────────────────────────────────
            if raw_text.strip():
                chunk_size = 800
                overlap = 100
                words = raw_text.split()
                for i in range(0, len(words), chunk_size - overlap):
                    chunk = " ".join(words[i:i + chunk_size])
                    if chunk.strip():
                        text_chunks.append(chunk)

        elapsed = (time.time() - start) * 1000

        _publish_event(job_id, {
            "event": "AGENT_COMPLETE",
            "job_id": job_id,
            "agent": "document",
            "data": {
                "processing_time_ms": elapsed,
                "chunks": len(text_chunks),
            },
        })

        return {
            "text_chunks": text_chunks,
            "processing_time_ms": elapsed,
        }

    except Exception as exc:
        elapsed = (time.time() - start) * 1000
        _publish_event(job_id, {
            "event": "AGENT_ERROR",
            "job_id": job_id,
            "agent": "document",
            "data": {"error": str(exc), "processing_time_ms": elapsed},
        })
        raise self.retry(exc=exc)

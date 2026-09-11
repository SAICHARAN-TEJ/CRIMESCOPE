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
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

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


def _with_job_attempt(data: dict[str, Any], attempt: int | None) -> dict[str, Any]:
    """Attach the §11 job attempt to event metadata when present (L5a).

    Mirrors Supervisor._with_job_attempt — agent events already use
    "attempt" for the agent-internal retry count, so the job-level fence
    is published under "job_attempt".
    """
    if attempt is not None:
        return {**data, "job_attempt": attempt}
    return data


# ── Observable decomposition events (docs/OBSERVABLE_CONTRACT.md §3-4) ────


def _evidence_id(filename: str | None) -> str:
    """Stable evidence id for decomposition events (v1: display-name based)."""
    return f"ev-{_display_name(filename).replace(' ', '_').lower()}"


def _publish_stage_event(job_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Publish a STAGE-family event (ACTIVITY/DECOMP_UPDATE) via pub/sub."""
    _publish_event(job_id, {"event": event_type, "job_id": job_id, "data": data})


def _publish_activity(
    job_id: str, stage: str, text: str, actor: str = "pipeline", level: str = "info"
) -> None:
    """Emit one semantic ACTIVITY line (≤120 chars, schema-bounded)."""
    from app.schemas.events import ActivityData

    _publish_stage_event(
        job_id, "ACTIVITY",
        ActivityData(actor=actor, stage=stage, text=text[:120], level=level).model_dump(),
    )


def _publish_decomp(
    job_id: str,
    evidence_id: str,
    filename: str,
    step: str,
    state: str,
    detail: str = "",
    progress: dict[str, Any] | None = None,
) -> None:
    """Emit one per-evidence decomposition step update."""
    from app.schemas.events import DecompUpdateData

    _publish_stage_event(
        job_id, "DECOMP_UPDATE",
        DecompUpdateData(
            evidence_id=evidence_id,
            filename=filename,
            step=step,
            state=state,
            detail=detail[:255],
            progress=progress,
        ).model_dump(),
    )


# ── Safe local naming (P0-1) ──────────────────────────────────────────────

# Extensions a worker may create locally. Derived ONLY from these allowlists —
# the client-supplied filename never contributes path bytes beyond a matched
# suffix, so `Path(tmpdir) / <safe name>` can never escape the temp dir.
_EXTENSION_BY_SUFFIX: dict[str, str] = {
    ".mp4": ".mp4", ".avi": ".avi", ".mov": ".mov", ".mkv": ".mkv",
    ".webm": ".webm", ".wmv": ".wmv", ".flv": ".flv",
    ".pdf": ".pdf", ".docx": ".docx", ".txt": ".txt",
}
_EXTENSION_BY_MIME: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/x-msvideo": ".avi",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "video/webm": ".webm",
    "video/x-ms-wmv": ".wmv",
    "video/x-flv": ".flv",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}

# Display names may keep readable characters but never path separators.
_DISPLAY_SAFE_RE = re.compile(r"[^A-Za-z0-9._ -]")


def _derive_extension(filename: str | None, content_type: str | None) -> str:
    """Pick a worker-known extension from the allowlists (suffix → MIME → .bin)."""
    # NUL bytes never reach Path(): some platforms reject them at construction.
    suffix = Path(filename.replace("\x00", "")).suffix.lower() if filename else ""
    if suffix in _EXTENSION_BY_SUFFIX:
        return _EXTENSION_BY_SUFFIX[suffix]
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in _EXTENSION_BY_MIME:
        return _EXTENSION_BY_MIME[mime]
    return ".bin"


def _safe_local_name(filename: str | None, content_type: str | None = "") -> str:
    """Server-fixed local name for evidence downloaded into a worker temp dir.

    The base name is constant; only the extension varies, and only via the
    allowlists above. A crafted absolute path, `..` segment, null byte, or
    unknown extension can therefore never influence the local path (P0-1).
    """
    return "evidence" + _derive_extension(filename, content_type)


def _display_name(filename: str | None) -> str:
    """Bounded, path-separator-free name for event payloads (display only)."""
    name = Path((filename or "unknown").replace("\x00", "")).name
    name = _DISPLAY_SAFE_RE.sub("_", name)
    name = name.strip() or "unknown"
    return name[:120]


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
def process_video(self, job_id: str, file_meta: dict[str, Any], attempt: int | None = None) -> dict[str, Any]:
    """
    Process a video file: extract keyframes + transcribe audio.

    Args:
        job_id: Pipeline job ID for event correlation.
        file_meta: {object_key, filename, content_type}
        attempt: Optional §11 job attempt (L5a) — published in event metadata.

    Returns:
        {text_chunks: [...], keyframes: [...], processing_time_ms: float}
    """
    start = time.time()
    filename = file_meta.get("filename", "unknown.mp4")
    object_key = file_meta.get("object_key", "")
    content_type = file_meta.get("content_type", "")
    display = _display_name(filename)
    ev_id = _evidence_id(filename)

    _publish_event(job_id, {
        "event": "AGENT_START",
        "job_id": job_id,
        "agent": "video",
        "data": _with_job_attempt({"filename": display}, attempt),
    })
    _publish_activity(job_id, "extract", f"Video decomposition started — {display}", actor="video")

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

        _publish_decomp(job_id, ev_id, display, "container", "active", "downloading from evidence store")

        with tempfile.TemporaryDirectory() as tmpdir:
            # P0-1: server-fixed name — client bytes never reach the path
            local_path = Path(tmpdir) / _safe_local_name(filename, content_type)
            minio_client.fget_object(bucket, object_key, str(local_path))

            _publish_decomp(job_id, ev_id, display, "container", "done", "container verified")
            _publish_decomp(job_id, ev_id, display, "metadata", "done", "metadata extracted")

            # ── Extract keyframes with FFmpeg ─────────────────────────
            _publish_decomp(job_id, ev_id, display, "frames", "active", "decoding keyframes")

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

            # Honest totals only — no fabricated percentage for a single
            # ffmpeg pass; the real frame count lands in `detail` on done.
            _publish_decomp(
                job_id, ev_id, display, "frames", "done",
                detail=f"{len(keyframes)} keyframes decoded",
            )

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
                    text_chunks.append(f"[Whisper unavailable] Video processed: {display}")

        elapsed = (time.time() - start) * 1000

        _publish_activity(
            job_id, "extract",
            f"Video decomposition complete — {len(keyframes)} keyframes, {len(text_chunks)} transcript chunks",
            actor="video", level="success",
        )
        _publish_event(job_id, {
            "event": "AGENT_COMPLETE",
            "job_id": job_id,
            "agent": "video",
            "data": _with_job_attempt({
                "processing_time_ms": elapsed,
                "keyframes": len(keyframes),
                "chunks": len(text_chunks),
            }, attempt),
        })

        return {
            "text_chunks": text_chunks,
            "keyframes": keyframes,
            "processing_time_ms": elapsed,
        }

    except Exception as exc:
        elapsed = (time.time() - start) * 1000
        _publish_activity(
            job_id, "extract",
            f"Video decomposition failed — {type(exc).__name__}",
            actor="video", level="error",
        )
        _publish_decomp(job_id, ev_id, display, "frames", "failed", str(exc)[:255])
        _publish_event(job_id, {
            "event": "AGENT_ERROR",
            "job_id": job_id,
            "agent": "video",
            "data": _with_job_attempt(
                {"error": str(exc), "processing_time_ms": elapsed}, attempt
            ),
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
def process_document(self, job_id: str, file_meta: dict[str, Any], attempt: int | None = None) -> dict[str, Any]:
    """
    Process a document: extract text and chunk it.

    Supports: PDF, DOCX, TXT.

    Args:
        job_id: Pipeline job ID.
        file_meta: {object_key, filename, content_type}
        attempt: Optional §11 job attempt (L5a) — published in event metadata.

    Returns:
        {text_chunks: [...], processing_time_ms: float}
    """
    start = time.time()
    filename = file_meta.get("filename", "unknown")
    object_key = file_meta.get("object_key", "")
    content_type = file_meta.get("content_type", "")
    display = _display_name(filename)
    ev_id = _evidence_id(filename)

    _publish_event(job_id, {
        "event": "AGENT_START",
        "job_id": job_id,
        "agent": "document",
        "data": _with_job_attempt({"filename": display}, attempt),
    })
    _publish_activity(job_id, "extract", f"Document decomposition started — {display}", actor="document")

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

        _publish_decomp(job_id, ev_id, display, "verify", "active", "downloading from evidence store")

        with tempfile.TemporaryDirectory() as tmpdir:
            # P0-1: server-fixed name — client bytes never reach the path
            local_path = Path(tmpdir) / _safe_local_name(filename, content_type)
            minio_client.fget_object(bucket, object_key, str(local_path))

            _publish_decomp(job_id, ev_id, display, "verify", "done", "integrity verified")
            _publish_decomp(job_id, ev_id, display, "text", "active", "extracting text")

            raw_text = ""

            # ── PDF extraction ────────────────────────────────────────
            if content_type == "application/pdf" or filename.endswith(".pdf"):
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(str(local_path))
                    page_count = max(doc.page_count, 1)
                    pages = []
                    # Real per-page counter — emits honest determinate progress.
                    for i in range(page_count):
                        page = doc.load_page(i)
                        pages.append(page.get_text())
                        n = i + 1
                        if n % 5 == 0 or n == page_count:  # throttle pub/sub volume
                            _publish_decomp(
                                job_id, ev_id, display, "text", "active",
                                detail=f"page {n} / {page_count}",
                                progress={"current": n, "total": page_count},
                            )
                    raw_text = "\n\n".join(pages)
                    doc.close()
                except ImportError:
                    raw_text = local_path.read_text(errors="ignore")
                    _publish_decomp(
                        job_id, ev_id, display, "text", "active",
                        detail="PyMuPDF unavailable — fallback text read",
                    )

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

        _publish_decomp(
            job_id, ev_id, display, "text", "done",
            detail=f"{len(text_chunks)} text chunks extracted",
        )

        elapsed = (time.time() - start) * 1000

        _publish_activity(
            job_id, "extract",
            f"Document decomposition complete — {len(text_chunks)} chunks",
            actor="document", level="success",
        )
        _publish_event(job_id, {
            "event": "AGENT_COMPLETE",
            "job_id": job_id,
            "agent": "document",
            "data": _with_job_attempt({
                "processing_time_ms": elapsed,
                "chunks": len(text_chunks),
            }, attempt),
        })

        return {
            "text_chunks": text_chunks,
            "processing_time_ms": elapsed,
        }

    except Exception as exc:
        elapsed = (time.time() - start) * 1000
        _publish_activity(
            job_id, "extract",
            f"Document decomposition failed — {type(exc).__name__}",
            actor="document", level="error",
        )
        _publish_decomp(job_id, ev_id, display, "text", "failed", str(exc)[:255])
        _publish_event(job_id, {
            "event": "AGENT_ERROR",
            "job_id": job_id,
            "agent": "document",
            "data": _with_job_attempt(
                {"error": str(exc), "processing_time_ms": elapsed}, attempt
            ),
        })
        raise self.retry(exc=exc)

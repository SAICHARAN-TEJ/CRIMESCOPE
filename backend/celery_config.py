"""
CrimeScope — Celery Configuration.

Redis-backed broker + result backend.
Separate queues for CPU-bound (video/doc) vs I/O-bound (graph) tasks.
Celery Beat schedule for write-behind graph buffer flush.
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import timedelta

# ── Broker / Backend ──────────────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

app = Celery(
    "crimescope",
    broker=REDIS_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.engine.tasks",
        "app.graph.buffer",
    ],
)

# ── Task Settings ─────────────────────────────────────────────────────────

app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_acks_late=True,                    # Ack after completion, not receipt
    worker_prefetch_multiplier=1,           # One task at a time per worker
    task_reject_on_worker_lost=True,        # Re-queue on worker crash
    task_track_started=True,                # Track STARTED state

    # Result expiry
    result_expires=3600,                    # 1 hour

    # Retry
    task_default_retry_delay=5,
    task_max_retries=3,

    # Concurrency — CPU workers get limited concurrency
    # Override per-worker with: celery -A celery_config worker --concurrency=2
    worker_concurrency=4,

    # Queues
    task_default_queue="default",
    task_routes={
        "app.engine.tasks.process_video": {"queue": "cpu_heavy"},
        "app.engine.tasks.process_document": {"queue": "cpu_heavy"},
        "app.graph.buffer.flush_graph_buffer": {"queue": "default"},
    },

    # Beat schedule — flush graph buffer every 2 seconds
    beat_schedule={
        "flush-graph-buffer": {
            "task": "app.graph.buffer.flush_graph_buffer",
            "schedule": timedelta(seconds=2),
        },
    },
)

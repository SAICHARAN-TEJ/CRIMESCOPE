"""
CrimeScope — MinIO Client with Pre-Signed URL Generation.

Security model:
  - Frontend gets a pre-signed PUT URL and uploads DIRECTLY to MinIO.
  - Backend never streams large files through the API.
  - Pre-signed URLs are generated against the PUBLIC endpoint
    (MINIO_ENDPOINT_PUBLIC) so browsers can reach them; internal operations
    (downloads, stat, bucket mgmt) use MINIO_ENDPOINT.
  - Downloads are streamed with a hard size cap (MAX_DOWNLOAD_MB).
  - Bucket creation is idempotent under concurrent startup.
  - All agent-facing helpers have async twins via asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger("crimescope.storage")

_RETRIES = 3
_RETRY_BASE_DELAY = 0.2  # seconds
_RETRY_MAX_DELAY = 2.0


class StorageError(Exception):
    """Typed MinIO/storage failure with bounded retry context."""

    def __init__(self, message: str, *, retriable: bool = False) -> None:
        super().__init__(message)
        self.retriable = retriable


def _sleep_with_jitter(attempt: int) -> float:
    return min(_RETRY_BASE_DELAY * (2**attempt) + random.uniform(0, 0.1), _RETRY_MAX_DELAY)


class MinIOClient:
    """Async-friendly MinIO wrapper for pre-signed URL operations."""

    def __init__(self) -> None:
        self.client: Minio | None = None          # internal endpoint (ops)
        self._public_client: Minio | None = None  # public endpoint (presign)
        self.connected: bool = False

    def connect(self) -> None:
        """Initialize both MinIO clients and ensure the bucket exists (idempotently)."""
        settings = get_settings()
        try:
            self.client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            # Presign client: uses the public endpoint when configured;
            # falls back to the internal endpoint (single-host deployments).
            presign_endpoint = settings.minio_endpoint_public or settings.minio_endpoint
            if presign_endpoint == settings.minio_endpoint:
                self._public_client = self.client
            else:
                self._public_client = Minio(
                    presign_endpoint,
                    access_key=settings.minio_access_key,
                    secret_key=settings.minio_secret_key,
                    secure=settings.minio_secure,
                )
            self._ensure_bucket(settings.minio_bucket)
            self.connected = True
            logger.info(
                f"MinIO connected: internal={settings.minio_endpoint} "
                f"presign={presign_endpoint} bucket={settings.minio_bucket}"
            )
        except Exception as e:
            logger.warning(f"MinIO connection failed: {e}")
            self.connected = False

    def _ensure_bucket(self, bucket: str) -> None:
        """Create the bucket if missing; concurrent creates are fine (M-36)."""
        assert self.client is not None
        try:
            if not self.client.bucket_exists(bucket):
                try:
                    self.client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
                except S3Error as e:
                    # BucketAlreadyOwnedByYou / BucketAlreadyExists → ok.
                    if e.code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                        pass
                    else:
                        raise
        except S3Error as e:
            if e.code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                return
            raise

    # ── Presigned URLs (public endpoint) ───────────────────────────────

    def generate_presigned_put(
        self,
        object_key: str,
        content_type: str = "application/octet-stream",
        expires: int = 600,
    ) -> str | None:
        """
        Generate a pre-signed PUT URL for direct frontend upload.

        Signed against the PUBLIC endpoint so browsers can reach it (§6).

        Args:
            object_key: The object path in MinIO (e.g., "uploads/abc123/video.mp4")
            content_type: MIME type for the upload
            expires: URL expiry in seconds (default 10 minutes)

        Returns:
            Pre-signed URL string, or None if MinIO is unavailable.
        """
        if not self.connected or not self._public_client:
            return None
        settings = get_settings()
        try:
            from datetime import timedelta

            url = self._public_client.presigned_put_object(
                settings.minio_bucket,
                object_key,
                expires=timedelta(seconds=expires),
            )
            logger.info(f"Generated presigned PUT: {object_key} (expires {expires}s)")
            return url
        except S3Error as e:
            logger.error(f"MinIO presigned URL failed: {e}")
            return None

    def generate_presigned_get(
        self,
        object_key: str,
        expires: int = 3600,
    ) -> str | None:
        """Generate a pre-signed GET URL for downloading (public endpoint)."""
        if not self.connected or not self._public_client:
            return None
        settings = get_settings()
        try:
            from datetime import timedelta

            url = self._public_client.presigned_get_object(
                settings.minio_bucket,
                object_key,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            logger.error(f"MinIO presigned GET failed: {e}")
            return None

    # ── Downloads (internal endpoint, capped streaming) ─────────────────

    def get_object_bytes(self, object_key: str) -> bytes | None:
        """
        Download an object's bytes with a hard size cap (H-6/M-19).

        Streams in bounded chunks; releases the response in finally.
        Raises StorageError when the object exceeds MAX_DOWNLOAD_MB.
        """
        if not self.connected or not self.client:
            return None
        settings = get_settings()
        max_bytes = settings.max_download_mb * 1024 * 1024
        response = None
        try:
            response = self.client.get_object(settings.minio_bucket, object_key)
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise StorageError(
                        f"Object {object_key} exceeds max download size "
                        f"({settings.max_download_mb} MB)"
                    )
                chunks.append(chunk)
            return b"".join(chunks)
        except StorageError:
            raise
        except Exception as e:
            logger.error(f"MinIO get_object failed for {object_key}: {e}")
            return None
        finally:
            if response is not None:
                try:
                    response.close()
                    response.release_conn()
                except Exception:
                    pass

    # ── Stat (size/content-type verification for /analysis/start) ──────

    def stat_object(self, object_key: str) -> Any | None:
        """Stat an object; returns minio ObjectStat or None."""
        if not self.connected or not self.client:
            return None
        settings = get_settings()
        try:
            return self.client.stat_object(settings.minio_bucket, object_key)
        except Exception as e:
            logger.warning(f"MinIO stat_object failed for {object_key}: {e}")
            return None

    # ── Async twins (asyncio.to_thread for agent paths, H-7) ───────────

    async def get_object_bytes_async(self, object_key: str) -> bytes | None:
        return await asyncio.to_thread(self.get_object_bytes, object_key)

    async def stat_object_async(self, object_key: str) -> Any | None:
        return await asyncio.to_thread(self.stat_object, object_key)

    async def generate_presigned_put_async(
        self, object_key: str, content_type: str = "application/octet-stream", expires: int = 600
    ) -> str | None:
        return await asyncio.to_thread(
            self.generate_presigned_put, object_key, content_type, expires
        )

    async def generate_presigned_get_async(self, object_key: str, expires: int = 3600) -> str | None:
        return await asyncio.to_thread(self.generate_presigned_get, object_key, expires)

    # ── Health ──────────────────────────────────────────────────────────

    def health(self) -> dict:
        """
        Health check. Reports `degraded` when connected but the required
        bucket is missing (M-35) so /healthz can fail readiness.
        """
        if not self.connected or not self.client:
            return {"status": "unavailable"}
        settings = get_settings()
        try:
            exists = self.client.bucket_exists(settings.minio_bucket)
            if not exists:
                return {"status": "degraded", "bucket_exists": False}
            return {"status": "ok", "bucket_exists": True}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# ── Module-level singleton ────────────────────────────────────────────────
_minio_client = MinIOClient()


def get_minio() -> MinIOClient:
    return _minio_client

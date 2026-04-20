"""
CrimeScope — MinIO Client with Pre-Signed URL Generation.

Security model:
  - Frontend gets a pre-signed PUT URL and uploads DIRECTLY to MinIO.
  - Backend never streams large files through the API.
  - Pre-signed URLs expire after configurable TTL.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger("crimescope.storage")


class MinIOClient:
    """Async-friendly MinIO wrapper for pre-signed URL operations."""

    def __init__(self) -> None:
        self.client: Optional[Minio] = None
        self.connected: bool = False

    def connect(self) -> None:
        """Initialize the MinIO client and ensure the bucket exists."""
        settings = get_settings()
        try:
            self.client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            # Ensure bucket exists
            bucket = settings.minio_bucket
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"Created MinIO bucket: {bucket}")
            self.connected = True
            logger.info(f"MinIO connected: {settings.minio_endpoint}")
        except Exception as e:
            logger.warning(f"MinIO connection failed: {e}")
            self.connected = False

    def generate_presigned_put(
        self,
        object_key: str,
        content_type: str = "application/octet-stream",
        expires: int = 3600,
    ) -> Optional[str]:
        """
        Generate a pre-signed PUT URL for direct frontend upload.

        Args:
            object_key: The object path in MinIO (e.g., "jobs/abc123/video.mp4")
            content_type: MIME type for the upload
            expires: URL expiry in seconds

        Returns:
            Pre-signed URL string, or None if MinIO is unavailable.
        """
        if not self.connected or not self.client:
            return None
        settings = get_settings()
        try:
            from datetime import timedelta
            url = self.client.presigned_put_object(
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
    ) -> Optional[str]:
        """Generate a pre-signed GET URL for downloading."""
        if not self.connected or not self.client:
            return None
        settings = get_settings()
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                settings.minio_bucket,
                object_key,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            logger.error(f"MinIO presigned GET failed: {e}")
            return None

    def get_object_bytes(self, object_key: str) -> Optional[bytes]:
        """Download an object's bytes (used by agents for processing)."""
        if not self.connected or not self.client:
            return None
        settings = get_settings()
        try:
            response = self.client.get_object(settings.minio_bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error(f"MinIO get_object failed for {object_key}: {e}")
            return None

    def health(self) -> dict:
        """Health check."""
        if not self.connected or not self.client:
            return {"status": "unavailable"}
        settings = get_settings()
        try:
            exists = self.client.bucket_exists(settings.minio_bucket)
            return {"status": "ok", "bucket_exists": exists}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# ── Module-level singleton ────────────────────────────────────────────────
_minio_client = MinIOClient()


def get_minio() -> MinIOClient:
    return _minio_client

"""
CrimeScope v4.4 — Hermetic Storage & Redis Client Tests.

All external I/O is mocked. No network, no MinIO, no Redis, no OpenRouter.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _restore_settings():
    """Keep tests hermetic: restore any mutated Settings attributes."""
    from app.core.config import get_settings

    settings = get_settings()
    original = settings.max_download_mb
    yield
    settings.max_download_mb = original


# ── Redis URL redaction (M-8) ────────────────────────────────────────────


class TestRedisURLRedaction:
    def test_password_masked(self):
        from app.core.redis_client import redact_url

        url = "redis://:supersecret@redis:6379/0"
        assert "supersecret" not in redact_url(url)
        assert ":***@" in redact_url(url)

    def test_user_password_masked(self):
        from app.core.redis_client import redact_url

        url = "redis://user:hunter2@redis:6379/0"
        redacted = redact_url(url)
        assert "hunter2" not in redacted
        assert "user" in redacted

    def test_no_credentials_unchanged(self):
        from app.core.redis_client import redact_url

        url = "redis://localhost:6379/0"
        assert redact_url(url) == url


# ── MinIO streaming download cap (H-6/M-19) ───────────────────────────────


class _FakeResponse:
    """Emulates a minio urllib3 response streaming in 1 MB chunks."""

    def __init__(self, total_mb: int):
        self._remaining = total_mb * 1024 * 1024
        self.closed = False
        self.released = False

    def read(self, size: int) -> bytes:
        if self._remaining <= 0:
            return b""
        chunk = b"x" * min(size, self._remaining)
        self._remaining -= len(chunk)
        return chunk

    def close(self):
        self.closed = True

    def release_conn(self):
        self.released = True


def _make_client(max_mb: int = 200):
    from app.core.config import get_settings
    from app.storage.minio_client import MinIOClient

    client = MinIOClient()
    client.connected = True
    client.client = MagicMock()

    get_settings().max_download_mb = max_mb
    return client


class TestMinIODownloadCap:
    def test_oversized_object_raises_storage_error(self):
        from app.storage.minio_client import StorageError

        client = _make_client(max_mb=5)
        client.client.get_object.return_value = _FakeResponse(total_mb=10)

        with pytest.raises(StorageError, match="max download size"):
            client.get_object_bytes("uploads/abc/huge.bin")

    def test_within_cap_returns_bytes(self):
        client = _make_client(max_mb=5)
        client.client.get_object.return_value = _FakeResponse(total_mb=2)

        data = client.get_object_bytes("uploads/abc/ok.bin")
        assert data == b"x" * (2 * 1024 * 1024)

    def test_response_released_even_on_error(self):
        from app.storage.minio_client import StorageError

        client = _make_client(max_mb=5)
        fake = _FakeResponse(total_mb=10)
        client.client.get_object.return_value = fake

        with pytest.raises(StorageError):
            client.get_object_bytes("uploads/abc/huge.bin")

        assert fake.closed is True      # finally released
        assert fake.released is True

    def test_unavailable_returns_none(self):
        from app.storage.minio_client import MinIOClient

        client = MinIOClient()  # never connected
        assert client.get_object_bytes("uploads/abc/x") is None


# ── MinIO degraded health (M-35) ──────────────────────────────────────────


class TestMinIOHealth:
    def test_degraded_when_bucket_missing(self):
        client = _make_client()
        client.client.bucket_exists.return_value = False

        health = client.health()
        assert health["status"] == "degraded"
        assert health["bucket_exists"] is False

    def test_ok_when_bucket_exists(self):
        client = _make_client()
        client.client.bucket_exists.return_value = True

        health = client.health()
        assert health["status"] == "ok"
        assert health["bucket_exists"] is True

    def test_unavailable_when_not_connected(self):
        from app.storage.minio_client import MinIOClient

        client = MinIOClient()
        assert client.health()["status"] == "unavailable"


# ── MinIO idempotent bucket create (M-36) ────────────────────────────────


class TestBucketIdempotency:
    def test_already_owned_by_you_is_ok(self):
        from minio.error import S3Error

        client = _make_client()
        client.client.bucket_exists.return_value = False

        def raise_already(*args, **kwargs):
            raise S3Error(
                code="BucketAlreadyOwnedByYou",
                message="owned",
                resource="bucket",
                request_id="x",
                host_id="x",
                response=MagicMock(),
            )

        client.client.make_bucket.side_effect = raise_already
        client._ensure_bucket("crimescope-evidence")  # must not raise

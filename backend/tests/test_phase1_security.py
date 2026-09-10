"""
CrimeScope — Phase 1 security acceptance tests.

Acceptance matrix for the Phase 1 security/ownership remediation:
  1-A  worker safe local naming — traversal corpus for _safe_local_name /
       _derive_extension / _display_name (P0-1)
  1-B  /analysis/start ownership validation (hard prefix + server-issued
       presign token, Redis-down degraded fallback — P0-2) plus upload
       request model bounds
  1-C  main.py lifespan wiring of validate_startup_security (P1)

validate_startup_security FUNCTION behavior (prod/dev × weak/strong) is
already covered by tests/test_security.py; only the lifespan wiring is
asserted here.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.db import repositories
from app.engine.tasks import (
    _derive_extension,
    _display_name,
    _safe_local_name,
)
from app.main import app

client = TestClient(app)


def _token() -> str:
    resp = client.post(
        "/api/v1/auth/token", json={"username": "admin", "password": "crimescope"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


# ── 1-A: safe worker local naming (P0-1) ──────────────────────────────────

_SAFE_NAME_CORPUS = [
    # (client filename, content_type, expected worker-local name)
    ("C:\\Windows\\System32\\evil.dll", "video/mp4", "evidence.mp4"),
    ("\\\\server\\share\\evil.exe", "application/pdf", "evidence.pdf"),
    ("../../etc/passwd.mp4", "", "evidence.mp4"),
    ("/etc/shadow", "", "evidence.bin"),
    ("archive.zip", "text/plain", "evidence.txt"),
    ("evil\x00.mp4", "", "evidence.mp4"),
    ("evidence.docx", "video/mp4", "evidence.docx"),
    ("semicolons;and$pecial#chars.docx", "", "evidence.docx"),
    (None, None, "evidence.bin"),
    ("", "video/x-msvideo", "evidence.avi"),
]


@pytest.mark.parametrize("filename,content_type,expected", _SAFE_NAME_CORPUS)
def test_safe_local_name_corpus(filename, content_type, expected):
    """Crafted paths, traversal, NULs, and unknown extensions can only ever
    produce a constant base name with an allowlisted extension."""
    assert _safe_local_name(filename, content_type) == expected


def test_safe_local_name_never_contains_path_bytes():
    evil = [
        "C:\\absolute\\path.mp4",
        "\\\\unc\\share\\path.mp4",
        "../../../../../../tmp/evil.mp4",
        "evil\x00name.mp4",
        "a/b\\c:d*e?f.mp4",
    ]
    pattern = re.compile(
        r"evidence\.(mp4|avi|mov|mkv|webm|wmv|flv|pdf|docx|txt|bin)"
    )
    for name in evil:
        safe = _safe_local_name(name, "video/mp4")
        assert pattern.fullmatch(safe)
        for bad in ("/", "\\", "..", "\x00", ":"):
            assert bad not in safe


def test_derive_extension_suffix_wins_over_mime():
    assert _derive_extension("clip.mp4", "application/pdf") == ".mp4"


def test_derive_extension_mime_parameters_ignored():
    assert _derive_extension("noext", "application/pdf; charset=binary") == ".pdf"


def test_derive_extension_unknown_everything_falls_back_to_bin():
    assert _derive_extension("thing.rar", "application/x-rar") == ".bin"


def test_display_name_keeps_readable_names():
    assert _display_name("report_final.pdf") == "report_final.pdf"
    assert _display_name("my evidence file.txt") == "my evidence file.txt"
    assert _display_name("a/b/c.mp4") == "c.mp4"


def test_display_name_replaces_unsafe_characters():
    assert _display_name("we!rd@name#.mp4") == "we_rd_name_.mp4"


def test_display_name_fallbacks():
    assert _display_name(None) == "unknown"
    assert _display_name("") == "unknown"


def test_display_name_strips_nul_bytes():
    assert _display_name("evil\x00name.mp4") == "evilname.mp4"


def test_display_name_reduces_traversal_to_final_segment():
    assert _display_name("../../etc/passwd") == "passwd"


def test_display_name_is_bounded_and_separator_free():
    for evil in ("C:\\evil\\x.mp4", "\\\\server\\share\\file.mp4"):
        display = _display_name(evil)
        assert display
        assert len(display) <= 120
        for sep in ("/", "\\"):
            assert sep not in display


def test_display_name_caps_length():
    assert len(_display_name("a" * 300)) == 120


# ── 1-B: upload ownership validation (P0-2) ───────────────────────────────


class _FakeRedis:
    """Test double matching the RedisClient surface the router uses."""

    def __init__(self, tokens: dict[str, str] | None = None, connected: bool = True):
        self.connected = connected
        self._tokens = dict(tokens or {})
        self.set_calls: list[tuple[str, str, int]] = []

    async def set(self, key: str, value: str, ex: int = 300) -> None:
        self.set_calls.append((key, value, ex))
        self._tokens[key] = value

    async def get(self, key: str) -> str | None:
        return self._tokens.get(key)


class _FakeMinio:
    def generate_presigned_put(
        self, object_key: str, content_type: str, expires: int = 600
    ) -> str:
        return f"http://minio.test/{object_key}"


def _start_payload(job_id: str, object_key: str) -> dict:
    return {
        "job_id": job_id,
        "files": [
            {
                "object_key": object_key,
                "filename": "evidence.mp4",
                "content_type": "video/mp4",
            }
        ],
        "question": "",
    }


async def _noop_pipeline(job_id, user_id, files, question, attempt=None):
    return None


@pytest.mark.asyncio
async def test_start_rejects_object_key_outside_user_prefix(monkeypatch):
    monkeypatch.setattr("app.api.router.get_redis", lambda: _FakeRedis(connected=True))
    resp = client.post(
        "/api/v1/analysis/start",
        headers=_auth(),
        json=_start_payload("job-own-prefix", "uploads/mallory/owner1/evidence.mp4"),
    )
    assert resp.status_code == 403
    assert await repositories.jobs.get("job-own-prefix") is None


@pytest.mark.asyncio
async def test_start_accepts_prefix_and_matching_presign_token(monkeypatch):
    key = "uploads/admin/owner1/evidence.mp4"
    fake = _FakeRedis(tokens={f"upload:presign:{key}": "admin"})
    monkeypatch.setattr("app.api.router.get_redis", lambda: fake)

    started: list[tuple] = []

    async def _record_pipeline(job_id, user_id, files, question, attempt=None):
        started.append((job_id, user_id, files, question))

    monkeypatch.setattr("app.api.router._run_pipeline", _record_pipeline)

    resp = client.post(
        "/api/v1/analysis/start",
        headers=_auth(),
        json=_start_payload("job-own-ok", key),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "job-own-ok"
    assert body["status"] == "queued"
    # Background pipeline dispatched with the validated payload
    assert started and started[0][0] == "job-own-ok"
    job = await repositories.jobs.get("job-own-ok", user_id="admin")
    assert job is not None


@pytest.mark.asyncio
async def test_start_rejects_valid_prefix_without_presign_token(monkeypatch):
    monkeypatch.setattr("app.api.router.get_redis", lambda: _FakeRedis(connected=True))
    resp = client.post(
        "/api/v1/analysis/start",
        headers=_auth(),
        json=_start_payload("job-own-token-miss", "uploads/admin/owner1/evidence.mp4"),
    )
    assert resp.status_code == 403
    assert await repositories.jobs.get("job-own-token-miss") is None


@pytest.mark.asyncio
async def test_start_rejects_presign_token_issued_to_other_user(monkeypatch):
    key = "uploads/admin/owner1/evidence.mp4"
    fake = _FakeRedis(tokens={f"upload:presign:{key}": "mallory"})
    monkeypatch.setattr("app.api.router.get_redis", lambda: fake)
    monkeypatch.setattr("app.api.router._run_pipeline", _noop_pipeline)
    resp = client.post(
        "/api/v1/analysis/start",
        headers=_auth(),
        json=_start_payload("job-own-token-other", key),
    )
    assert resp.status_code == 403
    assert await repositories.jobs.get("job-own-token-other") is None


@pytest.mark.asyncio
async def test_start_degrades_to_prefix_only_when_redis_down(monkeypatch):
    monkeypatch.setattr("app.api.router.get_redis", lambda: _FakeRedis(connected=False))
    monkeypatch.setattr("app.api.router._run_pipeline", _noop_pipeline)
    resp = client.post(
        "/api/v1/analysis/start",
        headers=_auth(),
        json=_start_payload("job-own-redis-down", "uploads/admin/owner1/evidence.mp4"),
    )
    assert resp.status_code == 200
    job = await repositories.jobs.get("job-own-redis-down", user_id="admin")
    assert job is not None


@pytest.mark.asyncio
async def test_presign_stores_server_issued_ownership_token(monkeypatch):
    fake_redis = _FakeRedis(connected=True)
    fake_minio = _FakeMinio()
    monkeypatch.setattr("app.api.router.get_redis", lambda: fake_redis)
    monkeypatch.setattr("app.api.router.get_minio", lambda: fake_minio)
    resp = client.post(
        "/api/v1/upload/presign",
        headers=_auth(),
        json={"filename": "evidence.mp4", "content_type": "video/mp4"},
    )
    assert resp.status_code == 200
    object_key = resp.json()["object_key"]
    assert object_key.startswith("uploads/admin/")
    assert object_key.endswith("/evidence.mp4")
    token_key = f"upload:presign:{object_key}"
    assert any(
        k == token_key and v == "admin" and ex == 86400
        for k, v, ex in fake_redis.set_calls
    )


def test_presign_rejects_oversized_filename():
    resp = client.post(
        "/api/v1/upload/presign",
        headers=_auth(),
        json={"filename": "x" * 256, "content_type": "video/mp4"},
    )
    assert resp.status_code == 422


def test_presign_rejects_oversized_content_type():
    resp = client.post(
        "/api/v1/upload/presign",
        headers=_auth(),
        json={"filename": "ok.mp4", "content_type": "x" * 129},
    )
    assert resp.status_code == 422


def test_start_rejects_oversized_object_key():
    resp = client.post(
        "/api/v1/analysis/start",
        headers=_auth(),
        json=_start_payload("job-own-toolong", "u" * 513),
    )
    assert resp.status_code == 422


def test_start_rejects_negative_file_size():
    payload = {
        "job_id": "job-own-negsize",
        "files": [
            {
                "object_key": "uploads/admin/owner1/evidence.mp4",
                "filename": "evidence.mp4",
                "content_type": "video/mp4",
                "file_size": -1,
            }
        ],
        "question": "",
    }
    resp = client.post("/api/v1/analysis/start", headers=_auth(), json=payload)
    assert resp.status_code == 422


# ── 1-C: startup security wiring (P1) ─────────────────────────────────────


def test_lifespan_invokes_startup_security_validation(monkeypatch):
    """main.py must route the startup gate through validate_startup_security
    (hard boot refusal in production) — not the old inline exact-string
    warning check."""
    import app.main as main_module

    calls: list[object] = []
    monkeypatch.setattr(
        main_module,
        "validate_startup_security",
        lambda settings: calls.append(settings),
    )
    with TestClient(main_module.app):
        pass  # enter/exit lifespan only
    assert len(calls) == 1

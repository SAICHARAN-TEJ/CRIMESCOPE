"""
CrimeScope — Tests for the Analysis Retry endpoint.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import repositories
from app.main import app
from app.schemas.events import JobStatus

client = TestClient(app)


def _token() -> str:
    resp = client.post("/api/v1/auth/token", json={"username": "admin", "password": "crimescope"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


async def _seed_job(job_id: str, status: str, user_id: str = "admin", **extra) -> None:
    await repositories.jobs.create(job_id, user_id, [], question="")
    await repositories.jobs.update_status(
        job_id, status, result_summary=extra.get("result"), error_message=extra.get("error_message")
    )


@pytest.mark.asyncio
async def test_retry_missing_job_returns_404():
    resp = client.post("/api/v1/analysis/nope/retry", headers=_auth())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_requires_auth():
    await _seed_job("job-auth", JobStatus.FAILED.value)
    resp = client.post("/api/v1/analysis/job-auth/retry")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_retry_failed_job_requeues():
    await _seed_job(
        "job-req",
        JobStatus.FAILED.value,
        result={"error": "boom"},
        error_message="boom",
    )
    resp = client.post("/api/v1/analysis/job-req/retry", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "job-req"
    assert body["status"] == JobStatus.QUEUED.value
    # Background re-run executes synchronously under TestClient
    job = await repositories.jobs.get("job-req")
    assert job is not None
    assert job.status != JobStatus.FAILED.value


@pytest.mark.asyncio
async def test_retry_completed_job_is_rejected():
    await _seed_job("job-done", JobStatus.COMPLETED.value)
    resp = client.post("/api/v1/analysis/job-done/retry", headers=_auth())
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_retry_respects_ownership():
    await _seed_job("job-owner", JobStatus.FAILED.value, user_id="someone-else")
    resp = client.post("/api/v1/analysis/job-owner/retry", headers=_auth())
    assert resp.status_code == 403
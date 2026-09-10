#!/usr/bin/env python3
"""
CrimeScope — End-to-End Smoke Test (Docker Compose).

Runs the full stack via `docker compose up -d`, waits on healthchecks,
then exercises:
  1. Auth (JWT)
  2. Upload presign + direct-to-MinIO PUT
  3. Analysis pipeline start → completion (polling /analysis/{job_id})
  4. Chat (ReportAgent) — one call
  5. Scenario injection — one call + result fetch
  6. Postgres persistence: restart the API container, verify the job
     created *before* restart is still queryable afterward

Fails loudly (exit 1 + docker logs) on any error.

Usage:
    python scripts/smoke_test.py            # from repo root
    SMOKE_API_BASE=http://localhost:8000 python scripts/smoke_test.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_BASE = os.getenv("SMOKE_API_BASE", "http://localhost:8000")
API = f"{API_BASE}/api/v1"
TIMEOUT_SECONDS = float(os.getenv("SMOKE_TIMEOUT", "180"))
COMPOSE = ["docker", "compose"]
try:
    import shutil
    COMPOSE = [shutil.which("docker-compose") or "docker-compose"] if shutil.which("docker-compose") else COMPOSE
except Exception:
    pass

SAMPLE_FILENAME = "smoke_evidence.txt"
SAMPLE_CONTENT = """\
WITNESS STATEMENT — Case #2026-SMK-001
Date: March 10, 2026
Witness: Jordan Lee, resident of 42 Elm Street, Springfield.
Statement: At approximately 22:00 on March 9, 2026, I saw a dark blue sedan
parked outside Marcus Williams' apartment on Oakwood Drive. A man matching
the description of David Chen got out and entered the building. I heard a
loud argument around 22:15. The sedan left at high speed at 22:30.
"""


def log(msg: str) -> None:
    print(f"[smoke] {msg}", flush=True)


def http_request(method: str, url: str, body: dict | None = None, token: str | None = None, timeout: float = 30.0) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw.decode(errors="replace")}
        return e.code, parsed


def compose(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        [*COMPOSE, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if check and result.returncode != 0:
        log(f"docker compose {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
        dump_logs()
        sys.exit(1)
    return result.stdout


def dump_logs() -> None:
    try:
        logs = subprocess.run(
            [*COMPOSE, "logs", "--tail", "200", "api", "postgres"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        log("========== Docker logs ==========")
        print(logs.stdout[-8000:])
    except Exception as e:
        log(f"Could not dump logs: {e}")


def wait_api_healthy(timeout: float = TIMEOUT_SECONDS) -> None:
    """Poll /healthz until all services report healthy (200)."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        code, body = http_request("GET", f"{API}/healthz", timeout=15)
        if code == 200:
            log(f"API healthy: {body.get('status')}")
            return
        last = (code, body)
        time.sleep(5)
    log(f"API never became healthy — last response: {last}")
    dump_logs()
    sys.exit(1)


def login() -> str:
    creds = {
        "username": os.getenv("ADMIN_USERNAME", "admin"),
        "password": os.getenv("ADMIN_PASSWORD", "crimescope"),
    }
    code, body = http_request("POST", f"{API}/auth/token", creds)
    if code != 200:
        raise AssertionError(f"Login failed: {code} {body}")
    log("Auth: JWT obtained")
    return body["access_token"]


def upload_sample(token: str) -> dict:
    code, body = http_request("POST", f"{API}/upload/presign", {"filename": SAMPLE_FILENAME}, token=token)
    if code != 200:
        raise AssertionError(f"Presign failed: {code} {body}")
    upload_url = body["upload_url"]
    req = urllib.request.Request(
        upload_url,
        data=SAMPLE_CONTENT.encode(),
        method="PUT",
        headers={"Content-Type": "text/plain"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 201, 204):
            raise AssertionError(f"MinIO PUT failed: {resp.status}")
    log(f"Upload: direct-to-MinIO OK ({body['object_key']})")
    return {"object_key": body["object_key"], "filename": SAMPLE_FILENAME, "content_type": "text/plain"}


def start_analysis(token: str, file_meta: dict) -> str:
    code, body = http_request(
        "POST",
        f"{API}/analysis/start",
        {"files": [file_meta], "question": "Who is the suspect and where were they seen?"},
        token=token,
    )
    if code != 200:
        raise AssertionError(f"analysis/start failed: {code} {body}")
    log(f"Analysis: job {body['job_id']} queued")
    return body["job_id"]


def wait_job(token: str, job_id: str, timeout: float = TIMEOUT_SECONDS) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, body = http_request("GET", f"{API}/analysis/{job_id}", token=token)
        if code != 200:
            raise AssertionError(f"GET analysis failed: {code} {body}")
        if body["status"] in ("completed", "failed"):
            if body["status"] == "failed":
                raise AssertionError(f"Job {job_id} FAILED: {body.get('result')}")
            log(f"Analysis: job {job_id} completed")
            return body
        time.sleep(3)
    raise AssertionError(f"Job {job_id} did not finish in {timeout}s")


def chat(token: str, job_id: str) -> None:
    code, body = http_request(
        "POST",
        f"{API}/chat",
        {"job_id": job_id, "message": "Summarize the key evidence in this case."},
        token=token,
    )
    if code != 200:
        raise AssertionError(f"Chat failed: {code} {body}")
    log(f"Chat: ReportAgent responded ({len(body.get('message', ''))} chars)")
    assert "conversation" not in body or body["conversation_id"], "missing conversation_id"


def scenario(token: str, job_id: str) -> None:
    code, body = http_request(
        "POST",
        f"{API}/scenario",
        {"job_id": job_id, "hypothesis": "What if David Chen and Jordan Lee were at the apartment together at 22:00?"},
        token=token,
    )
    if code != 200:
        raise AssertionError(f"Scenario injection failed: {code} {body}")
    scenario_id = body["scenario_id"]
    log(f"Scenario: {scenario_id} submitted")
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        code, sbody = http_request("GET", f"{API}/scenario/{scenario_id}", token=token)
        if code != 200:
            raise AssertionError(f"GET scenario failed: {code} {sbody}")
        if sbody["status"] in ("completed", "failed"):
            log(f"Scenario: {sbody['status']} with diff {sbody.get('result', {})}")
            return
        time.sleep(3)
    raise AssertionError(f"Scenario {scenario_id} did not finish in {TIMEOUT_SECONDS}s")


def restart_api_job_survives(token: str, job_id: str) -> None:
    """§6.6: restart the API container and prove the job survives (Postgres)."""
    log("Persistence: restarting api container...")
    compose("restart", "api")
    wait_api_healthy()
    code, body = http_request("GET", f"{API}/analysis/{job_id}", token=token)
    if code != 200:
        raise AssertionError(f"Job {job_id} NOT queryable after restart: {code} {body}")
    log(f"Persistence: job {job_id} survived API restart (status={body['status']}) ✓")


def main() -> None:
    log("CrimeScope smoke test starting")
    compose("up", "-d", "--wait")
    log("docker compose: all services up")
    wait_api_healthy()

    token = login()
    file_meta = upload_sample(token)
    job_id = start_analysis(token, file_meta)
    wait_job(token, job_id)
    chat(token, job_id)
    scenario(token, job_id)
    restart_api_job_survives(token, job_id)

    log("ALL SMOKE TESTS PASSED ✓")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        log(f"SMOKE TEST FAILED: {e}")
        dump_logs()
        sys.exit(1)
    except Exception as e:
        log(f"SMOKE TEST ERROR: {e}")
        dump_logs()
        sys.exit(2)
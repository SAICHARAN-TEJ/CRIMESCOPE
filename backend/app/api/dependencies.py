"""
CrimeScope — FastAPI Dependencies.

Shared dependencies injected into route handlers:
  - rate_limit: Redis sliding window rate limiter (fail-open)
  - rate_limit_auth: fail-closed variant for /auth/token
  - inject_correlation_id: bounded, validated correlation IDs (M-12)
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import Request

from app.core.logger import reset_correlation_id, set_correlation_id
from app.core.security import rate_limiter

# Bounded correlation IDs: 1-64 chars of [A-Za-z0-9_.-] (M-12).
_CORRELATION_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


async def rate_limit(request: Request) -> None:
    """Dependency that enforces per-IP rate limiting via Redis (fail-open)."""
    await rate_limiter.check(request)


async def rate_limit_auth(request: Request) -> None:
    """Fail-closed rate limiting for authentication endpoints (§4)."""
    await rate_limiter.check_auth(request)


async def inject_correlation_id(request: Request) -> str:
    """
    Generate or extract a correlation ID for distributed tracing.

    Client-supplied X-Correlation-ID values are validated (bounded length +
    charset); invalid values are replaced with a server-generated ID.
    The contextvar is reset in finally so it never leaks across requests.
    """
    raw = request.headers.get("X-Correlation-ID", "")
    if raw and _CORRELATION_ID_RE.fullmatch(raw):
        cid = raw
    else:
        cid = uuid.uuid4().hex
    token = set_correlation_id(cid)
    try:
        return cid
    finally:
        reset_correlation_id(token)


def verify_job_ownership(user: dict[str, Any], job_user_id: str) -> None:
    """
    Zero-trust ownership check.
    Raises 403 if token.sub != job.user_id.
    """
    from fastapi import HTTPException, status

    if user.get("sub") != job_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this job",
        )

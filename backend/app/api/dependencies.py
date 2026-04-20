"""
CrimeScope — FastAPI Dependencies.

Shared dependencies injected into route handlers:
  - get_current_user: JWT validation
  - rate_limit: Redis sliding window rate limiter
  - correlation_id_middleware: Attach correlation IDs to requests
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, Request

from app.core.logger import set_correlation_id
from app.core.security import get_current_user as _get_user, rate_limiter


async def require_auth(user: dict[str, Any] = Depends(_get_user)) -> dict[str, Any]:
    """Dependency that requires a valid JWT. Returns decoded token payload."""
    return user


async def rate_limit(request: Request) -> None:
    """Dependency that enforces per-IP rate limiting via Redis."""
    await rate_limiter.check(request)


async def inject_correlation_id(request: Request) -> str:
    """
    Generate or extract a correlation ID for distributed tracing.
    Sets it in contextvars so the JSON logger includes it automatically.
    """
    cid = request.headers.get("X-Correlation-ID", uuid.uuid4().hex)
    set_correlation_id(cid)
    return cid


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

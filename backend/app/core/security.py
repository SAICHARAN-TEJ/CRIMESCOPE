"""
CrimeScope — JWT Authentication & Redis Rate Limiter.

Security layer:
  1. JWT validation for REST + WebSocket
  2. Sliding window rate limiter backed by Redis
  3. Password hashing utilities
  4. Prompt injection sanitizer
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings

# ── Password Hashing ──────────────────────────────────────────────────────
# Using hashlib + secrets for Python 3.14 compatibility.
# In production, swap for argon2-cffi.

import hashlib
import secrets

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, digest = hashed.split("$", 1)
        return hashlib.sha256(f"{salt}{plain}".encode()).hexdigest() == digest
    except ValueError:
        return False


# ── JWT Token Management ──────────────────────────────────────────────────


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT with configurable expiry."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("sub") is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing sub")
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency — extracts and validates the JWT from the Authorization header."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    return decode_token(credentials.credentials)


def validate_ws_token(token: str) -> dict[str, Any]:
    """Validate JWT for WebSocket connections (no Depends available)."""
    return decode_token(token)


# ── Rate Limiter ──────────────────────────────────────────────────────────


class RateLimiter:
    """Redis-backed sliding window rate limiter."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def check(self, request: Request) -> None:
        """Raise 429 if the client exceeds rate limits."""
        from app.core.redis_client import get_redis

        redis = get_redis()
        if redis is None or not redis.connected:
            return  # Fail open if Redis unavailable

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window = self._settings.rate_limit_window_seconds
        limit = self._settings.rate_limit_requests

        pipe = redis.client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        count = results[2]

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit} requests per {window}s",
            )


rate_limiter = RateLimiter()


# ── Prompt Injection Sanitizer ────────────────────────────────────────────

_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions",
    r"disregard\s+(everything|all|previous)",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions?:",
    r"system\s*:",
    r"<\s*/?script",
    r"```\s*(system|assistant)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_input(text: str) -> str:
    """Remove potential prompt injection patterns from user input."""
    cleaned = _INJECTION_RE.sub("[REDACTED]", text)
    # Strip control characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    return cleaned.strip()

"""
CrimeScope — JWT Authentication & Redis Rate Limiter.

Security layer:
  1. JWT validation for REST + WebSocket (generic client-facing errors)
  2. Sliding window rate limiter backed by Redis (fail-closed for auth)
  3. Password hashing — bcrypt (cost 12) with legacy sha256 verification
     and a rehash-upgrade indicator
  4. Prompt injection sanitizer
  5. AUTH_ENABLED toggle — disabled returns an explicit dev principal
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings

logger = logging.getLogger("crimescope.security")

bearer_scheme = HTTPBearer(auto_error=False)

# ── Password Hashing (bcrypt + legacy sha256 upgrade path) ────────────────

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")
_BCRYPT_COST = 12
_LEGACY_HEX_LEN = 64  # sha256 hexdigest length


def _is_bcrypt_hash(hashed: str) -> bool:
    return hashed.startswith(_BCRYPT_PREFIXES)


def _is_legacy_hash(hashed: str) -> bool:
    """Old format: `<32-hex-char-salt>$<64-hex-char-sha256-digest>`."""
    try:
        salt, digest = hashed.split("$", 1)
    except ValueError:
        return False
    return (
        len(salt) == 32
        and len(digest) == _LEGACY_HEX_LEN
        and re.fullmatch(r"[0-9a-fA-F]+", salt) is not None
        and re.fullmatch(r"[0-9a-fA-F]+", digest) is not None
    )


def hash_password(password: str) -> str:
    """Hash with bcrypt (cost 12). Output: standard $2b$ digest."""
    import bcrypt

    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_COST)
    ).decode("utf-8")


def _verify_legacy(plain: str, hashed: str) -> bool:
    salt, digest = hashed.split("$", 1)
    computed = hashlib.sha256(f"{salt}{plain}".encode()).hexdigest()
    return hmac.compare_digest(computed, digest)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time verification. Supports bcrypt + legacy sha256 digests."""
    try:
        if _is_bcrypt_hash(hashed):
            import bcrypt

            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        if _is_legacy_hash(hashed):
            return _verify_legacy(plain, hashed)
        return False
    except (ValueError, TypeError):
        return False


def needs_rehash(plain: str, hashed: str) -> bool:
    """True when the stored hash verifies but is not current bcrypt (cost 12).

    Login flows should rehash + persist when this returns True.
    """
    if not verify_password(plain, hashed):
        return False
    if not _is_bcrypt_hash(hashed):
        return True
    try:
        # bcrypt digest encodes its cost at chars 4..6, e.g. "$2b$12$..."
        cost = int(hashed[4:6])
    except (ValueError, IndexError):
        return True
    return cost < _BCRYPT_COST


# ── JWT Token Management ──────────────────────────────────────────────────


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT with configurable expiry."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises HTTPException on failure.

    Client-facing error text is generic (M-11); specifics are logged server-side.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as e:
        logger.warning(f"JWT validation failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency — extracts and validates the JWT.

    When AUTH_ENABLED=false, returns an explicit dev principal so the local
    single-user flow keeps working without tokens (§1 of the master plan).
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return {"sub": "local-user", "username": "dev", "dev": True}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


async def get_admin_user(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Admin-gated dependency for debug/ops endpoints (§21).

    Login (L4) embeds `is_admin` from the User table (L6) into the token.
    The dev principal is trusted only when auth is explicitly disabled.
    """
    if user.get("dev") and not get_settings().auth_enabled:
        return user
    if user.get("is_admin") is True:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrator privileges required",
    )


def validate_ws_token(token: str) -> dict[str, Any]:
    """Validate JWT for WebSocket connections (no Depends available)."""
    settings = get_settings()
    if not settings.auth_enabled:
        return {"sub": "local-user", "username": "dev", "dev": True}
    return decode_token(token)


# ── Rate Limiter ──────────────────────────────────────────────────────────


class RateLimiter:
    """Redis-backed sliding window rate limiter.

    Redis-outage policy (§4): fail CLOSED (503) for authentication endpoints,
    fail OPEN (allow + warn) everywhere else.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def check(self, request: Request, *, fail_closed: bool = False) -> None:
        """Raise 429 if the client exceeds rate limits.

        Raises 503 when Redis is down and fail_closed=True (auth endpoints).
        """
        from app.core.redis_client import get_redis

        redis = get_redis()
        if redis is None or not redis.connected or not redis.client:
            if fail_closed:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiter unavailable — authentication temporarily disabled",
                )
            return  # Fail open if Redis unavailable

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window = self._settings.rate_limit_window_seconds
        limit = self._settings.rate_limit_per_minute

        try:
            pipe = redis.client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = await pipe.execute()
        except Exception as e:
            logger.warning(f"Rate limiter Redis error: {type(e).__name__}: {e}")
            if fail_closed:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiter unavailable — authentication temporarily disabled",
                )
            return  # Fail open on transient Redis errors

        count = results[2]

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit} requests per {window}s",
            )

    async def check_auth(self, request: Request) -> None:
        """Fail-closed variant for /auth/token."""
        await self.check(request, fail_closed=True)


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

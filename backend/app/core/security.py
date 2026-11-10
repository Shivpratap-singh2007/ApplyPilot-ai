"""Authentication, password hashing, JWT, CSRF, and rate-limiting helpers."""

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
import hmac
import re
import secrets
import threading
import time
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import jwt
from jwt import InvalidTokenError

from app.core.config import get_settings

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

_PASSWORD_LETTER_RE = re.compile(r"[A-Za-z]")
_PASSWORD_DIGIT_OR_SYMBOL_RE = re.compile(r"[0-9!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]")


def validate_password_strength(password: str) -> None:
    """Enforce baseline password quality without truncating user passwords."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters.")
    if not _PASSWORD_LETTER_RE.search(password) or not _PASSWORD_DIGIT_OR_SYMBOL_RE.search(password):
        raise ValueError("Password must contain at least one letter and one number or symbol.")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored Argon2id hash."""
    try:
        return _password_hasher.verify(hashed_password, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token for the given user ID."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate an access token, returning None if invalid or expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
    except InvalidTokenError:
        return None
    if payload.get("type") != "access" or not isinstance(payload.get("sub"), str):
        return None
    return payload


def generate_csrf_token() -> str:
    """Generate a high-entropy CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_tokens(cookie_token: str | None, header_token: str | None) -> bool:
    """Constant-time validation of double-submit CSRF cookie and header tokens."""
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter keyed by client identifier."""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """Record an attempt and return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - bucket[0])) + 1)
                return False, retry_after
            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        """Clear all tracked buckets (used in tests)."""
        with self._lock:
            self._buckets.clear()


auth_rate_limiter = SlidingWindowRateLimiter()


"""FastAPI dependencies for authentication, CSRF verification, and rate limiting."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import auth_rate_limiter, decode_access_token, verify_csrf_tokens
from app.db.session import get_db
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_client_ip(request: Request) -> str:
    """Extract client IP address safely without trusting spoofable headers by default."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_auth(request: Request) -> None:
    """Enforce sliding-window rate limits on authentication endpoints."""
    settings = get_settings()
    client_ip = get_client_ip(request)
    key = f"auth:{request.url.path}:{client_ip}"
    allowed, retry_after = auth_rate_limiter.is_allowed(
        key=key,
        max_requests=settings.auth_rate_limit_requests,
        window_seconds=settings.auth_rate_limit_window_seconds,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit_automation(request: Request) -> None:
    """Enforce sliding-window rate limits on browser automation endpoints to protect local RAM."""
    client_ip = get_client_ip(request)
    key = f"auto:{request.url.path}:{client_ip}"
    allowed, retry_after = auth_rate_limiter.is_allowed(
        key=key,
        max_requests=30,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many automation requests. Please wait briefly before trying again.",
            headers={"Retry-After": str(retry_after)},
        )


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User:
    """Authenticate current user via Bearer token or HttpOnly session cookie (with CSRF check)."""
    settings = get_settings()
    token: str | None = None
    via_cookie = False

    if bearer is not None and bearer.credentials:
        token = bearer.credentials
    else:
        cookie_token = request.cookies.get(settings.session_cookie_name)
        if cookie_token:
            token = cookie_token
            via_cookie = True

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if via_cookie and request.method.upper() in _UNSAFE_METHODS:
        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        csrf_header = request.headers.get("X-CSRF-Token")
        if not verify_csrf_tokens(csrf_cookie, csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing or invalid.",
            )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


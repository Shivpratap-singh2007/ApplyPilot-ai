"""Authentication endpoints: register, login, logout, current user, CSRF token."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, rate_limit_auth
from app.core.config import get_settings
from app.core.security import create_access_token, generate_csrf_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, MessageResponse, RegisterRequest, UserRead
from app.services.audit_service import record_audit_event
from app.services.auth_service import (
    EmailAlreadyExistsError,
    InactiveAccountError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, csrf_token: str) -> None:
    """Attach HttpOnly session cookie and readable CSRF double-submit cookie."""
    settings = get_settings()
    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie(
        key=settings.session_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=max_age,
        path="/",
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Register a new ApplyPilot AI user account."""
    try:
        user = register_user(db, payload, ip_address=get_client_ip(request))
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    access_token = create_access_token(user.id)
    csrf_token = generate_csrf_token()
    _set_auth_cookies(response, access_token, csrf_token)
    return AuthResponse(
        access_token=access_token,
        csrf_token=csrf_token,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit_auth)],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Authenticate an existing user and issue session credentials."""
    try:
        user = authenticate_user(db, payload, ip_address=get_client_ip(request))
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveAccountError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    access_token = create_access_token(user.id)
    csrf_token = generate_csrf_token()
    _set_auth_cookies(response, access_token, csrf_token)
    return AuthResponse(
        access_token=access_token,
        csrf_token=csrf_token,
        user=UserRead.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """Clear authentication cookies and record logout in audit logs."""
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    record_audit_event(
        db,
        event_type="auth.logout",
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=get_client_ip(request),
    )
    return MessageResponse(message="Logged out successfully.")


@router.get("/csrf")
def get_csrf(request: Request, response: Response) -> dict[str, str]:
    """Return or initialize the CSRF token for browser cookie sessions."""
    settings = get_settings()
    token = request.cookies.get(settings.csrf_cookie_name) or generate_csrf_token()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return {"csrf_token": token}


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Return the currently authenticated user's account summary."""
    return UserRead.model_validate(current_user)


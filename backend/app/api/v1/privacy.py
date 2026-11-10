"""Settings, audit log, data export, and account deletion endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.privacy import (
    AccountDeleteRequest,
    AuditLogRead,
    SettingsRead,
    SettingsUpdateRequest,
)
from app.services.privacy_service import (
    PrivacyVerificationError,
    delete_user_account_and_data,
    export_user_data,
    get_user_settings,
    list_user_audit_logs,
    update_user_settings,
)

settings_router = APIRouter(prefix="/settings", tags=["settings"])
privacy_router = APIRouter(prefix="/privacy", tags=["privacy"])


@settings_router.get("", response_model=SettingsRead)
def read_settings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SettingsRead:
    """Return local AI preferences and SaaS usage metrics."""
    return get_user_settings(db, current_user)


@settings_router.patch("", response_model=SettingsRead)
def save_settings(
    payload: SettingsUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SettingsRead:
    """Update user's preferred local Ollama model."""
    return update_user_settings(db, current_user, payload, ip_address=get_client_ip(request))


@privacy_router.get("/audit-logs", response_model=list[AuditLogRead])
def read_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AuditLogRead]:
    """List recent audit events for the authenticated user."""
    logs = list_user_audit_logs(db, current_user)
    return [AuditLogRead.model_validate(item) for item in logs]


@privacy_router.get("/export")
def export_my_data(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Export all data owned by the authenticated user as JSON."""
    return export_user_data(db, current_user, ip_address=get_client_ip(request))


@privacy_router.post("/delete-account", response_model=MessageResponse)
def delete_my_account(
    payload: AccountDeleteRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """Permanently purge user account, profile, resumes, applications, and local files."""
    try:
        delete_user_account_and_data(
            db,
            current_user,
            password=payload.password,
            confirm_phrase=payload.confirm_phrase,
        )
    except PrivacyVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    cfg = get_settings()
    response.delete_cookie(cfg.session_cookie_name, path="/")
    response.delete_cookie(cfg.csrf_cookie_name, path="/")
    return MessageResponse(message="Account and all associated local data have been deleted.")


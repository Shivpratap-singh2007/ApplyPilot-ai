"""Audit logging service for security-sensitive and workflow events."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog

_SENSITIVE_KEYS = frozenset({"password", "hashed_password", "token", "access_token", "secret", "otp", "cookie"})


def _sanitize_details(details: dict[str, Any] | None) -> dict[str, Any]:
    """Strip any accidentally passed sensitive keys before persisting audit details."""
    if not details:
        return {}
    return {
        k: ("[REDACTED]" if k.lower() in _SENSITIVE_KEYS else v)
        for k, v in details.items()
    }


def record_audit_event(
    db: Session,
    *,
    event_type: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    """Persist an immutable audit log entry."""
    entry = AuditLog(
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details_json=_sanitize_details(details),
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry


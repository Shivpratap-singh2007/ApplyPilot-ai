"""Settings, usage summary, audit log inspection, data export, and account deletion services."""

import shutil
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import decrypt_text
from app.core.security import verify_password
from app.models.application import Application, ApplicationStateTransition, ApprovalSnapshot
from app.models.audit import AuditLog
from app.models.resume import Resume
from app.models.subscription import Subscription
from app.models.usage import UsageEvent
from app.models.user import User
from app.schemas.privacy import SettingsRead, SettingsUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.profile_service import get_or_create_profile


class PrivacyVerificationError(ValueError):
    """Raised when destructive privacy action confirmation fails."""


def get_user_settings(db: Session, user: User) -> SettingsRead:
    """Return user AI model preference, local Ollama defaults, and SaaS usage metrics."""
    settings = get_settings()
    events = list(db.scalars(select(UsageEvent).where(UsageEvent.user_id == user.id)))
    summary: dict[str, int] = {}
    for ev in events:
        summary[ev.event_type] = summary.get(ev.event_type, 0) + ev.units

    return SettingsRead(
        preferred_ollama_model=user.preferred_ollama_model,
        default_ollama_model=settings.ollama_model,
        fallback_ollama_model=settings.ollama_fallback_model,
        ollama_base_url=settings.ollama_base_url,
        allow_localhost_automation=settings.allow_localhost_automation,
        plan_tier=user.plan_tier,
        usage_summary=summary,
    )


def update_user_settings(
    db: Session,
    user: User,
    payload: SettingsUpdateRequest,
    *,
    ip_address: str | None = None,
) -> SettingsRead:
    """Update user's local Ollama model preference."""
    user.preferred_ollama_model = (payload.preferred_ollama_model or "").strip() or None
    db.add(user)
    record_audit_event(
        db,
        event_type="settings.updated",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip_address,
        details={"preferred_ollama_model": user.preferred_ollama_model},
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return get_user_settings(db, user)


def list_user_audit_logs(db: Session, user: User, limit: int = 100) -> list[AuditLog]:
    """Return audit events strictly owned by the authenticated user."""
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.user_id == user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    )


def export_user_data(db: Session, user: User, *, ip_address: str | None = None) -> dict[str, Any]:
    """Export all user-owned data as a structured JSON dictionary without password hashes."""
    profile = get_or_create_profile(db, user)
    resumes = list(db.scalars(select(Resume).where(Resume.user_id == user.id)))
    applications = list(db.scalars(select(Application).where(Application.user_id == user.id)))
    approvals = list(db.scalars(select(ApprovalSnapshot).where(ApprovalSnapshot.user_id == user.id)))
    subscription = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    app_ids = [a.id for a in applications]
    transitions = (
        list(
            db.scalars(
                select(ApplicationStateTransition).where(
                    ApplicationStateTransition.application_id.in_(app_ids)
                )
            )
        )
        if app_ids
        else []
    )
    audit_logs = list_user_audit_logs(db, user, limit=500)

    record_audit_event(
        db,
        event_type="privacy.data_exported",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip_address,
    )

    return {
        "account": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "plan_tier": user.plan_tier,
            "preferred_ollama_model": user.preferred_ollama_model,
            "created_at": user.created_at.isoformat(),
        },
        "subscription": (
            {
                "plan_code": subscription.plan_code,
                "status": subscription.status,
                "monthly_application_limit": subscription.monthly_application_limit,
            }
            if subscription
            else None
        ),
        "profile": {
            c.name: getattr(profile, c.name)
            for c in profile.__table__.columns
            if c.name not in {"created_at", "updated_at"}
        },
        "resumes": [
            {
                "id": r.id,
                "label": r.label,
                "original_filename": r.original_filename,
                "file_size_bytes": r.file_size_bytes,
                "sha256_hash": r.sha256_hash,
                "extracted_text": decrypt_text(r.extracted_text),
                "extracted_data_json": r.extracted_data_json,
                "is_verified": r.is_verified,
                "is_preferred": r.is_preferred,
                "created_at": r.created_at.isoformat(),
            }
            for r in resumes
        ],
        "applications": [
            {
                "id": a.id,
                "target_url": a.target_url,
                "application_type": a.application_type,
                "title": a.title,
                "company_or_org": a.company_or_org,
                "status": a.status,
                "confirmation_reference": a.confirmation_reference,
                "created_at": a.created_at.isoformat(),
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            }
            for a in applications
        ],
        "approval_snapshots": [
            {
                "id": s.id,
                "application_id": s.application_id,
                "snapshot_hash": s.snapshot_hash,
                "is_consumed": s.is_consumed,
                "approved_at": s.approved_at.isoformat(),
            }
            for s in approvals
        ],
        "state_transitions": [
            {
                "application_id": t.application_id,
                "from_status": t.from_status,
                "to_status": t.to_status,
                "reason": t.reason,
                "created_at": t.created_at.isoformat(),
            }
            for t in transitions
        ],
        "audit_logs": [
            {
                "event_type": log.event_type,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details_json": log.details_json,
                "created_at": log.created_at.isoformat(),
            }
            for log in audit_logs
        ],
    }


def delete_user_account_and_data(
    db: Session,
    user: User,
    *,
    password: str,
    confirm_phrase: str,
) -> None:
    """Verify password and explicit confirmation phrase before purging all user files and DB records."""
    if confirm_phrase.strip().upper() != "DELETE":
        raise PrivacyVerificationError("Type DELETE to confirm permanent account removal.")
    if not verify_password(password, user.hashed_password):
        raise PrivacyVerificationError("Password verification failed.")

    settings = get_settings()
    user_id = user.id
    user_upload_dir = (settings.upload_dir / user_id).resolve()
    user_shot_dir = (settings.screenshot_dir / user_id).resolve()

    db.delete(user)
    db.commit()

    if settings.upload_dir.resolve() in user_upload_dir.parents and user_upload_dir.is_dir():
        shutil.rmtree(user_upload_dir, ignore_errors=True)
    if settings.screenshot_dir.resolve() in user_shot_dir.parents and user_shot_dir.is_dir():
        shutil.rmtree(user_shot_dir, ignore_errors=True)


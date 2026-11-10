"""Application orchestration, approval snapshots, and controlled submission service."""

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.application import Application, ApplicationStateTransition, ApprovalSnapshot
from app.models.resume import Resume
from app.models.usage import UsageEvent
from app.models.user import User
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationDraftUpdateRequest,
    ApplicationRead,
    ApplicationStatsRead,
    ApprovalSnapshotRead,
    StateTransitionRead,
)
from app.services.agent_bridge import (
    UnsafeURLError,
    build_profile_context,
    compute_form_structure_hash,
    create_ollama_provider,
    create_playwright_worker,
    validate_target_url,
)
from app.services.audit_service import record_audit_event
from app.services.profile_service import get_or_create_profile
from app.services.resume_service import get_user_resume_or_raise, resolve_resume_abs_path
from app.services.state_machine import InvalidStateTransitionError, transition_application_state

from applypilot_agent.ai.schemas import FormFieldDescriptor


class ApplicationNotFoundError(LookupError):
    """Raised when an application does not exist or belongs to another user."""


class ApplicationValidationError(ValueError):
    """Raised when application input, URL, or required review fields are invalid."""


class ApprovalConflictError(ValueError):
    """Raised on unauthorized submission, stale approval, or duplicate submission attempt."""


def _compute_snapshot_hash(
    *,
    target_url: str,
    resume_sha256: str | None,
    form_structure_hash: str,
    approved_values: dict[str, str],
) -> str:
    payload = json.dumps(
        {
            "target_url": target_url,
            "resume_sha256": resume_sha256 or "",
            "form_structure_hash": form_structure_hash,
            "approved_values": approved_values,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _merge_approved_values(application: Application) -> dict[str, str]:
    merged: dict[str, str] = {}
    for match in application.draft_matches_json or []:
        fid = str(match.get("field_id", ""))
        if fid:
            merged[fid] = str(match.get("proposed_value", "") or "")
    for fid, val in (application.edited_values_json or {}).items():
        merged[str(fid)] = str(val or "")
    return merged


def _compute_missing_required(
    detected_fields: list[dict[str, Any]],
    merged_values: dict[str, str],
    has_resume: bool,
) -> list[str]:
    missing: list[str] = []
    for raw_field in detected_fields:
        if not raw_field.get("required"):
            continue
        fid = str(raw_field.get("field_id", ""))
        label = str(raw_field.get("label") or raw_field.get("name") or fid)
        if raw_field.get("input_type") == "file":
            if not has_resume and not merged_values.get(fid, "").strip():
                missing.append(label)
        elif not merged_values.get(fid, "").strip():
            missing.append(label)
    return missing


def _record_usage(db: Session, user_id: str, event_type: str, metadata: dict[str, Any] | None = None) -> None:
    db.add(
        UsageEvent(
            user_id=user_id,
            event_type=event_type,
            units=1,
            metadata_json=metadata or {},
        )
    )


def get_application_for_user(db: Session, user: User, application_id: str) -> Application:
    """Fetch an application strictly owned by the authenticated user."""
    app_obj = db.scalar(
        select(Application).where(Application.id == application_id, Application.user_id == user.id)
    )
    if app_obj is None:
        raise ApplicationNotFoundError("Application not found.")
    return app_obj


def serialize_application(db: Session, app_obj: Application) -> ApplicationRead:
    """Serialize Application along with its transition timeline and latest approval snapshot."""
    transitions = list(
        db.scalars(
            select(ApplicationStateTransition)
            .where(ApplicationStateTransition.application_id == app_obj.id)
            .order_by(ApplicationStateTransition.created_at.asc())
        )
    )
    latest_snapshot = db.scalar(
        select(ApprovalSnapshot)
        .where(ApprovalSnapshot.application_id == app_obj.id)
        .order_by(ApprovalSnapshot.approved_at.desc())
        .limit(1)
    )
    return ApplicationRead(
        id=app_obj.id,
        user_id=app_obj.user_id,
        resume_id=app_obj.resume_id,
        target_url=app_obj.target_url,
        application_type=app_obj.application_type,
        title=app_obj.title,
        company_or_org=app_obj.company_or_org,
        status=app_obj.status,
        detected_fields_json=list(app_obj.detected_fields_json or []),
        draft_matches_json=list(app_obj.draft_matches_json or []),
        edited_values_json=dict(app_obj.edited_values_json or {}),
        validation_warnings_json=list(app_obj.validation_warnings_json or []),
        missing_fields_json=list(app_obj.missing_fields_json or []),
        has_draft_screenshot=bool(app_obj.draft_screenshot_rel_path),
        has_confirmation_screenshot=bool(app_obj.confirmation_screenshot_rel_path),
        confirmation_reference=app_obj.confirmation_reference,
        confirmation_evidence_json=app_obj.confirmation_evidence_json,
        error_message=app_obj.error_message,
        ai_provider_used=app_obj.ai_provider_used,
        created_at=app_obj.created_at,
        updated_at=app_obj.updated_at,
        submitted_at=app_obj.submitted_at,
        transitions=[StateTransitionRead.model_validate(t) for t in transitions],
        latest_approval=ApprovalSnapshotRead.model_validate(latest_snapshot) if latest_snapshot else None,
    )


def create_application(
    db: Session,
    user: User,
    payload: ApplicationCreateRequest,
    *,
    ip_address: str | None = None,
) -> Application:
    """Validate URL/resume ownership and create a new application in CREATED state."""
    settings = get_settings()
    try:
        validated = validate_target_url(
            payload.target_url,
            allow_localhost=settings.allow_localhost_automation,
        )
    except UnsafeURLError as exc:
        raise ApplicationValidationError(str(exc)) from exc

    profile = get_or_create_profile(db, user)
    resume_id: str | None = payload.resume_id or profile.preferred_resume_id
    if resume_id:
        get_user_resume_or_raise(db, user, resume_id)

    app_obj = Application(
        user_id=user.id,
        resume_id=resume_id,
        target_url=validated.url,
        application_type=payload.application_type,
        title=payload.title.strip() if payload.title else None,
        company_or_org=payload.company_or_org.strip() if payload.company_or_org else None,
        status="CREATED",
        allow_localhost=settings.allow_localhost_automation,
    )
    db.add(app_obj)
    db.flush()
    db.add(
        ApplicationStateTransition(
            application_id=app_obj.id,
            from_status=None,
            to_status="CREATED",
            reason="Application created by user.",
        )
    )
    _record_usage(db, user.id, "application.created", {"application_id": app_obj.id})
    record_audit_event(
        db,
        event_type="application.created",
        user_id=user.id,
        resource_type="application",
        resource_id=app_obj.id,
        ip_address=ip_address,
        details={"target_url": validated.url, "application_type": payload.application_type},
        commit=False,
    )
    db.commit()
    db.refresh(app_obj)
    return app_obj


def run_draft_pipeline(application_id: str, bind_engine: Any) -> None:
    """
    Execute URL validation, DOM inspection, hybrid matching, and non-submitting draft fill.

    Uses a dedicated sessionmaker bound to the caller's engine so background tasks work cleanly
    against both production databases and isolated test databases.
    """
    settings = get_settings()
    SessionMaker = sessionmaker(bind=bind_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with SessionMaker() as db:
        app_obj = db.get(Application, application_id)
        if app_obj is None or app_obj.status == "CANCELLED":
            return
        user = db.get(User, app_obj.user_id)
        if user is None:
            return

        try:
            transition_application_state(db, app_obj, "VALIDATING_URL", reason="Validating target URL.")
            validate_target_url(app_obj.target_url, allow_localhost=app_obj.allow_localhost)

            transition_application_state(db, app_obj, "OPENING_PAGE", reason="Opening target page in isolated Playwright context.")
            transition_application_state(db, app_obj, "ANALYZING_FORM", reason="Inspecting DOM controls and challenges.")
            transition_application_state(db, app_obj, "MATCHING_PROFILE", reason="Matching verified profile fields and local AI fallback.")
            transition_application_state(db, app_obj, "FILLING_DRAFT", reason="Filling draft form controls without submitting.")

            profile = get_or_create_profile(db, user)
            resume = get_user_resume_or_raise(db, user, app_obj.resume_id) if app_obj.resume_id else None
            profile_ctx = build_profile_context(profile, resume)

            user_shot_dir = settings.screenshot_dir / user.id
            user_shot_dir.mkdir(parents=True, exist_ok=True)
            shot_rel = f"{user.id}/{app_obj.id}_draft.png"
            shot_abs = (settings.screenshot_dir / shot_rel).resolve()

            worker = create_playwright_worker()
            ollama = create_ollama_provider(user)
            result = worker.inspect_and_fill_draft(
                url=app_obj.target_url,
                profile=profile_ctx,
                ai_provider=ollama,
                screenshot_path=shot_abs,
                allow_localhost=app_obj.allow_localhost,
            )

            app_obj.detected_fields_json = [f.model_dump() for f in result.fields]
            app_obj.draft_matches_json = [m.model_dump() for m in result.matches]
            app_obj.missing_fields_json = list(result.missing_required_fields)
            app_obj.validation_warnings_json = list(result.validation_errors) + list(result.ai_warnings)
            app_obj.ai_provider_used = result.ai_provider_used
            app_obj.error_message = result.challenge_reason
            if not app_obj.title and (result.heading or result.page_title):
                app_obj.title = (result.heading or result.page_title)[:300]
            if result.screenshot_path and shot_abs.is_file():
                app_obj.draft_screenshot_rel_path = shot_rel

            _record_usage(db, user.id, "application.draft_filled", {"application_id": app_obj.id})
            transition_application_state(
                db,
                app_obj,
                result.status,
                reason=result.challenge_reason
                or (
                    "Missing required fields require user input."
                    if result.status == "WAITING_FOR_USER_INPUT"
                    else "Draft ready for human review and approval."
                ),
            )
        except Exception as exc:
            app_obj.error_message = f"{type(exc).__name__}: {exc}"
            if app_obj.status not in {"FAILED", "CANCELLED", "SUBMITTED"}:
                transition_application_state(
                    db,
                    app_obj,
                    "FAILED",
                    reason=app_obj.error_message[:480],
                )


def update_draft(
    db: Session,
    user: User,
    application_id: str,
    payload: ApplicationDraftUpdateRequest,
    *,
    ip_address: str | None = None,
) -> Application:
    """Save user edits to draft values/resume, invalidating any prior approval snapshot."""
    app_obj = get_application_for_user(db, user, application_id)
    if app_obj.status in {"SUBMITTING", "VERIFYING", "SUBMITTED", "CANCELLED"}:
        raise ApprovalConflictError(f"Cannot edit an application in '{app_obj.status}' state.")

    if payload.resume_id is not None:
        if payload.resume_id:
            get_user_resume_or_raise(db, user, payload.resume_id)
        app_obj.resume_id = payload.resume_id or None

    if payload.title is not None:
        app_obj.title = payload.title.strip() or None
    if payload.company_or_org is not None:
        app_obj.company_or_org = payload.company_or_org.strip() or None

    current_edits = dict(app_obj.edited_values_json or {})
    for k, v in payload.edited_values.items():
        current_edits[str(k)] = str(v)
    app_obj.edited_values_json = current_edits

    merged = _merge_approved_values(app_obj)
    has_resume = bool(app_obj.resume_id)
    missing = _compute_missing_required(app_obj.detected_fields_json or [], merged, has_resume)
    app_obj.missing_fields_json = missing

    if app_obj.status == "APPROVED":
        transition_application_state(
            db,
            app_obj,
            "WAITING_FOR_REVIEW",
            reason="Draft values or resume edited after approval; fresh review required.",
            commit=False,
        )
    elif app_obj.status == "WAITING_FOR_USER_INPUT" and not missing and not app_obj.error_message:
        transition_application_state(
            db,
            app_obj,
            "WAITING_FOR_REVIEW",
            reason="Required missing fields filled by user; ready for final review.",
            commit=False,
        )

    record_audit_event(
        db,
        event_type="application.draft_updated",
        user_id=user.id,
        resource_type="application",
        resource_id=app_obj.id,
        ip_address=ip_address,
        details={"edited_keys": sorted(payload.edited_values.keys())},
        commit=False,
    )
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    return app_obj


def approve_application(
    db: Session,
    user: User,
    application_id: str,
    *,
    ip_address: str | None = None,
) -> ApprovalSnapshot:
    """Lock an immutable ApprovalSnapshot and transition application to APPROVED."""
    app_obj = get_application_for_user(db, user, application_id)
    if app_obj.status not in {"WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT"}:
        raise ApprovalConflictError(
            f"Application in '{app_obj.status}' state cannot be approved."
        )

    merged_values = _merge_approved_values(app_obj)
    resume: Resume | None = None
    if app_obj.resume_id:
        resume = get_user_resume_or_raise(db, user, app_obj.resume_id)

    missing = _compute_missing_required(
        app_obj.detected_fields_json or [],
        merged_values,
        has_resume=resume is not None,
    )
    if missing:
        app_obj.missing_fields_json = missing
        db.add(app_obj)
        db.commit()
        raise ApplicationValidationError(
            f"Cannot approve while required fields are missing: {', '.join(missing)}"
        )

    fields = [FormFieldDescriptor.model_validate(item) for item in (app_obj.detected_fields_json or [])]
    form_structure_hash = compute_form_structure_hash(app_obj.target_url, fields)
    resume_sha = resume.sha256_hash if resume else None
    snapshot_hash = _compute_snapshot_hash(
        target_url=app_obj.target_url,
        resume_sha256=resume_sha,
        form_structure_hash=form_structure_hash,
        approved_values=merged_values,
    )

    snapshot = ApprovalSnapshot(
        application_id=app_obj.id,
        user_id=user.id,
        target_url=app_obj.target_url,
        resume_id=resume.id if resume else None,
        resume_sha256=resume_sha,
        approved_values_json=merged_values,
        form_structure_hash=form_structure_hash,
        snapshot_hash=snapshot_hash,
        is_consumed=False,
    )
    db.add(snapshot)
    transition_application_state(
        db,
        app_obj,
        "APPROVED",
        reason="User explicitly approved immutable form snapshot.",
        commit=False,
    )
    record_audit_event(
        db,
        event_type="application.approved",
        user_id=user.id,
        resource_type="application",
        resource_id=app_obj.id,
        ip_address=ip_address,
        details={"snapshot_hash": snapshot_hash},
        commit=False,
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


def submit_approved_application(
    db: Session,
    user: User,
    application_id: str,
    *,
    ip_address: str | None = None,
) -> Application:
    """Independently validate explicit approval snapshot and perform controlled submission."""
    settings = get_settings()
    app_obj = get_application_for_user(db, user, application_id)

    if app_obj.status == "SUBMITTED":
        raise ApprovalConflictError("Duplicate submission blocked: application is already submitted.")
    if app_obj.status == "UNKNOWN":
        raise ApprovalConflictError(
            "Submission outcome is UNKNOWN; automatic retry is disabled to prevent duplicates."
        )
    if app_obj.status != "APPROVED":
        raise ApprovalConflictError(
            f"Explicit user approval is required before submission (current status: '{app_obj.status}')."
        )

    snapshot = db.scalar(
        select(ApprovalSnapshot)
        .where(
            ApprovalSnapshot.application_id == app_obj.id,
            ApprovalSnapshot.user_id == user.id,
            ApprovalSnapshot.is_consumed.is_(False),
        )
        .order_by(ApprovalSnapshot.approved_at.desc())
        .limit(1)
    )
    if snapshot is None:
        raise ApprovalConflictError("No active unconsumed approval snapshot found; fresh review required.")

    resume: Resume | None = None
    if app_obj.resume_id:
        resume = get_user_resume_or_raise(db, user, app_obj.resume_id)

    fields = [FormFieldDescriptor.model_validate(item) for item in (app_obj.detected_fields_json or [])]
    current_structure_hash = compute_form_structure_hash(app_obj.target_url, fields)
    current_merged_values = _merge_approved_values(app_obj)
    expected_hash = _compute_snapshot_hash(
        target_url=app_obj.target_url,
        resume_sha256=resume.sha256_hash if resume else None,
        form_structure_hash=current_structure_hash,
        approved_values=current_merged_values,
    )
    if expected_hash != snapshot.snapshot_hash or snapshot.target_url != app_obj.target_url:
        transition_application_state(
            db,
            app_obj,
            "WAITING_FOR_REVIEW",
            reason="Application state diverged from approved snapshot; fresh review required.",
        )
        raise ApprovalConflictError("Approved snapshot no longer matches current draft; fresh review required.")

    # Consume snapshot atomically before launching browser submission to block duplicates.
    snapshot.is_consumed = True
    snapshot.consumed_at = datetime.now(UTC)
    db.add(snapshot)
    transition_application_state(
        db,
        app_obj,
        "SUBMITTING",
        reason="Submitting approved snapshot via Playwright worker.",
    )

    resume_abs = str(resolve_resume_abs_path(resume)) if resume else None
    shot_rel = f"{user.id}/{app_obj.id}_confirm.png"
    shot_abs = (settings.screenshot_dir / shot_rel).resolve()
    shot_abs.parent.mkdir(parents=True, exist_ok=True)

    worker = create_playwright_worker()
    try:
        result = worker.submit_approved_application(
            url=snapshot.target_url,
            approved_values=snapshot.approved_values_json,
            expected_form_structure_hash=snapshot.form_structure_hash,
            resume_file_path=resume_abs,
            screenshot_path=shot_abs,
            allow_localhost=app_obj.allow_localhost,
        )
    except Exception as exc:
        app_obj.error_message = f"{type(exc).__name__}: {exc}"
        transition_application_state(
            db,
            app_obj,
            "UNKNOWN",
            reason="Unexpected exception during submission; marked UNKNOWN to prevent duplicate submit.",
        )
        db.refresh(app_obj)
        return app_obj

    if result.screenshot_path and shot_abs.is_file():
        app_obj.confirmation_screenshot_rel_path = shot_rel

    if result.status == "REQUIRES_NEW_REVIEW":
        app_obj.error_message = result.error_message
        transition_application_state(db, app_obj, "WAITING_FOR_REVIEW", reason=result.error_message or "Form changed.")
    elif result.status == "WAITING_FOR_USER_INPUT":
        app_obj.error_message = result.error_message
        transition_application_state(
            db,
            app_obj,
            "WAITING_FOR_USER_INPUT",
            reason=result.error_message or "Human intervention required.",
        )
    else:
        transition_application_state(db, app_obj, "VERIFYING", reason="Verifying post-submission page evidence.")
        app_obj.validation_warnings_json = list(result.validation_errors)
        app_obj.confirmation_evidence_json = result.confirmation_evidence or None
        app_obj.confirmation_reference = result.confirmation_reference
        app_obj.error_message = result.error_message
        if result.status == "SUBMITTED":
            app_obj.submitted_at = datetime.now(UTC)
            _record_usage(db, user.id, "application.submitted", {"application_id": app_obj.id})
        transition_application_state(
            db,
            app_obj,
            result.status,
            reason=result.error_message or f"Submission resolved with status {result.status}.",
        )

    record_audit_event(
        db,
        event_type=f"application.submit.{app_obj.status.lower()}",
        user_id=user.id,
        resource_type="application",
        resource_id=app_obj.id,
        ip_address=ip_address,
        details={"confirmation_reference": app_obj.confirmation_reference},
    )
    db.refresh(app_obj)
    return app_obj


def retry_application_draft(
    db: Session,
    user: User,
    application_id: str,
    *,
    ip_address: str | None = None,
) -> Application:
    """Safely re-run form inspection and drafting ONLY from non-submitted recoverable states."""
    app_obj = get_application_for_user(db, user, application_id)
    if app_obj.status not in {"FAILED", "WAITING_FOR_USER_INPUT", "WAITING_FOR_REVIEW"}:
        raise InvalidStateTransitionError(
            f"Cannot re-inspect application from '{app_obj.status}' state."
        )
    previous_status = app_obj.status
    app_obj.error_message = None
    app_obj.status = "CREATED"
    db.add(
        ApplicationStateTransition(
            application_id=app_obj.id,
            from_status=previous_status,
            to_status="CREATED",
            reason="User requested safe re-inspection.",
        )
    )
    record_audit_event(
        db,
        event_type="application.requeued",
        user_id=user.id,
        resource_type="application",
        resource_id=app_obj.id,
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(app_obj)
    return app_obj


def cancel_application(
    db: Session,
    user: User,
    application_id: str,
    *,
    ip_address: str | None = None,
) -> Application:
    """Cancel an unsubmitted application."""
    app_obj = get_application_for_user(db, user, application_id)
    transition_application_state(
        db,
        app_obj,
        "CANCELLED",
        reason="Cancelled by user.",
        commit=False,
    )
    record_audit_event(
        db,
        event_type="application.cancelled",
        user_id=user.id,
        resource_type="application",
        resource_id=app_obj.id,
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(app_obj)
    return app_obj


def manual_complete_application(
    db: Session,
    user: User,
    application_id: str,
    *,
    confirmed_manually: bool,
    confirmation_reference: str | None = None,
    notes: str | None = None,
    ip_address: str | None = None,
) -> Application:
    """Record explicit user confirmation when completing an application manually."""
    if not confirmed_manually:
        raise ApplicationValidationError("Manual submission confirmation must be checked.")
    app_obj = get_application_for_user(db, user, application_id)
    if app_obj.status in {"SUBMITTED", "CANCELLED", "SUBMITTING", "VERIFYING"}:
        raise ApprovalConflictError(
            f"Cannot mark application manually submitted from '{app_obj.status}' state."
        )
    if app_obj.status not in {"WAITING_FOR_USER_INPUT", "WAITING_FOR_REVIEW", "APPROVED", "FAILED"}:
        raise ApprovalConflictError(
            f"Application in '{app_obj.status}' state is not eligible for manual completion."
        )

    previous = app_obj.status
    app_obj.status = "SUBMITTED"
    app_obj.submitted_at = datetime.now(UTC)
    app_obj.error_message = None
    app_obj.confirmation_reference = (confirmation_reference or "").strip() or None
    app_obj.confirmation_evidence_json = {
        "mode": "manual_assisted",
        "notes": (notes or "").strip(),
    }
    db.add(app_obj)
    db.add(
        ApplicationStateTransition(
            application_id=app_obj.id,
            from_status=previous,
            to_status="SUBMITTED",
            reason="Manual-assisted submission confirmed by user.",
        )
    )
    _record_usage(db, user.id, "application.manual_submitted", {"application_id": app_obj.id})
    record_audit_event(
        db,
        event_type="application.submit.manual_assisted",
        user_id=user.id,
        resource_type="application",
        resource_id=app_obj.id,
        ip_address=ip_address,
        details={"confirmation_reference": app_obj.confirmation_reference},
        commit=False,
    )
    db.commit()
    db.refresh(app_obj)
    return app_obj


def list_applications(
    db: Session,
    user: User,
    *,
    status_filter: str | None = None,
    search: str | None = None,
) -> list[Application]:
    """List applications belonging to the authenticated user with optional search and status filter."""
    stmt = select(Application).where(Application.user_id == user.id)
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    rows = list(db.scalars(stmt.order_by(Application.created_at.desc())))
    if search:
        q = search.strip().lower()
        rows = [
            row
            for row in rows
            if q in (row.title or "").lower()
            or q in (row.company_or_org or "").lower()
            or q in row.target_url.lower()
            or q in (row.confirmation_reference or "").lower()
        ]
    return rows


def get_application_stats(db: Session, user: User) -> ApplicationStatsRead:
    """Compute dashboard summary counts strictly scoped to the authenticated user."""
    rows = list(db.scalars(select(Application.status).where(Application.user_id == user.id)))
    draft_states = {"CREATED", "VALIDATING_URL", "OPENING_PAGE", "ANALYZING_FORM", "MATCHING_PROFILE", "FILLING_DRAFT", "WAITING_FOR_USER_INPUT"}
    review_states = {"WAITING_FOR_REVIEW", "APPROVED", "SUBMITTING", "VERIFYING"}
    return ApplicationStatsRead(
        total=len(rows),
        drafts=sum(1 for s in rows if s in draft_states),
        awaiting_review=sum(1 for s in rows if s in review_states),
        submitted=sum(1 for s in rows if s == "SUBMITTED"),
        failed=sum(1 for s in rows if s == "FAILED"),
        unknown=sum(1 for s in rows if s == "UNKNOWN"),
        cancelled=sum(1 for s in rows if s == "CANCELLED"),
    )


def resolve_screenshot_abs_path(db: Session, user: User, application_id: str, kind: str) -> Path | None:
    """Resolve draft or confirmation screenshot path inside SCREENSHOT_DIR after ownership check."""
    app_obj = get_application_for_user(db, user, application_id)
    rel = app_obj.draft_screenshot_rel_path if kind == "draft" else app_obj.confirmation_screenshot_rel_path
    if not rel:
        return None
    base = get_settings().screenshot_dir.resolve()
    target = (base / rel).resolve()
    if base not in target.parents or not target.is_file():
        return None
    return target

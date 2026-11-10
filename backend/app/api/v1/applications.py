"""Application workflow API routes: create, draft, edit, approve, submit, track, screenshots."""

from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, rate_limit_automation
from app.db.session import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationDraftUpdateRequest,
    ApplicationRead,
    ApplicationStatsRead,
    ApprovalSnapshotRead,
    ManualCompleteRequest,
)
from app.services.application_service import (
    ApplicationNotFoundError,
    ApplicationValidationError,
    ApprovalConflictError,
    approve_application,
    cancel_application,
    create_application,
    get_application_for_user,
    get_application_stats,
    list_applications,
    manual_complete_application,
    resolve_screenshot_abs_path,
    retry_application_draft,
    run_draft_pipeline,
    serialize_application,
    submit_approved_application,
    update_draft,
)
from app.services.resume_service import ResumeNotFoundError
from app.services.state_machine import InvalidStateTransitionError

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/stats", response_model=ApplicationStatsRead)
def read_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplicationStatsRead:
    """Return dashboard counts across application lifecycle buckets."""
    return get_application_stats(db, current_user)


@router.get("", response_model=list[ApplicationRead])
def get_applications(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=200),
) -> list[ApplicationRead]:
    """List applications belonging strictly to the authenticated user."""
    rows = list_applications(db, current_user, status_filter=status_filter, search=search)
    return [serialize_application(db, row) for row in rows]


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_automation)],
)
def start_application(
    payload: ApplicationCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplicationRead:
    """Create an application record and launch non-submitting inspection & draft filling."""
    try:
        app_obj = create_application(
            db,
            current_user,
            payload,
            ip_address=get_client_ip(request),
        )
    except (ApplicationValidationError, ResumeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    bind_engine = db.get_bind()
    if payload.run_immediately:
        run_draft_pipeline(app_obj.id, bind_engine)
        db.expire_all()
        app_obj = get_application_for_user(db, current_user, app_obj.id)
    else:
        background_tasks.add_task(run_draft_pipeline, app_obj.id, bind_engine)

    return serialize_application(db, app_obj)


@router.get("/{application_id}", response_model=ApplicationRead)
def read_application(
    application_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplicationRead:
    """Fetch full details and state transitions for one user-owned application."""
    try:
        app_obj = get_application_for_user(db, current_user, application_id)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return serialize_application(db, app_obj)


@router.patch("/{application_id}/draft", response_model=ApplicationRead)
def edit_application_draft(
    application_id: str,
    payload: ApplicationDraftUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplicationRead:
    """Edit proposed field values or attached resume (invalidates prior approvals)."""
    try:
        app_obj = update_draft(
            db,
            current_user,
            application_id,
            payload,
            ip_address=get_client_ip(request),
        )
    except (ApplicationNotFoundError, ResumeNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApprovalConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return serialize_application(db, app_obj)


@router.post("/{application_id}/approve", response_model=ApprovalSnapshotRead)
def approve_application_endpoint(
    application_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApprovalSnapshotRead:
    """Explicitly approve the current reviewed form values and create an immutable snapshot."""
    try:
        snapshot = approve_application(
            db,
            current_user,
            application_id,
            ip_address=get_client_ip(request),
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApplicationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (ApprovalConflictError, InvalidStateTransitionError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ApprovalSnapshotRead.model_validate(snapshot)


@router.post(
    "/{application_id}/submit",
    response_model=ApplicationRead,
    dependencies=[Depends(rate_limit_automation)],
)
def submit_application_endpoint(
    application_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplicationRead:
    """Submit an explicitly approved application after independent snapshot verification."""
    try:
        app_obj = submit_approved_application(
            db,
            current_user,
            application_id,
            ip_address=get_client_ip(request),
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ApprovalConflictError, InvalidStateTransitionError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return serialize_application(db, app_obj)


@router.post("/{application_id}/retry", response_model=ApplicationRead)
def retry_application_endpoint(
    application_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    run_immediately: bool = Query(default=False),
) -> ApplicationRead:
    """Re-run form inspection & draft filling safely from FAILED or WAITING states."""
    try:
        app_obj = retry_application_draft(
            db,
            current_user,
            application_id,
            ip_address=get_client_ip(request),
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    bind_engine = db.get_bind()
    if run_immediately:
        run_draft_pipeline(app_obj.id, bind_engine)
        db.expire_all()
        app_obj = get_application_for_user(db, current_user, app_obj.id)
    else:
        background_tasks.add_task(run_draft_pipeline, app_obj.id, bind_engine)
    return serialize_application(db, app_obj)


@router.post("/{application_id}/cancel", response_model=ApplicationRead)
def cancel_application_endpoint(
    application_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplicationRead:
    """Cancel an unsubmitted application."""
    try:
        app_obj = cancel_application(
            db,
            current_user,
            application_id,
            ip_address=get_client_ip(request),
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return serialize_application(db, app_obj)


@router.post("/{application_id}/manual-complete", response_model=ApplicationRead)
def manual_complete_endpoint(
    application_id: str,
    payload: ManualCompleteRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApplicationRead:
    """Record a manual-assisted submission when automated submit is unsupported or blocked."""
    try:
        app_obj = manual_complete_application(
            db,
            current_user,
            application_id,
            confirmed_manually=payload.confirmed_manually,
            confirmation_reference=payload.confirmation_reference,
            notes=payload.notes,
            ip_address=get_client_ip(request),
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApplicationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ApprovalConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return serialize_application(db, app_obj)


@router.get("/{application_id}/screenshots/{kind}")
def get_application_screenshot(
    application_id: str,
    kind: Literal["draft", "confirmation"],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Serve user-isolated draft or confirmation screenshots safely."""
    try:
        path = resolve_screenshot_abs_path(db, current_user, application_id, kind)
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not available.")
    return FileResponse(path, media_type="image/png")


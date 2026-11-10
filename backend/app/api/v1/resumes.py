"""Resume upload, listing, extraction verification, and deletion endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.profile import ProfileRead
from app.schemas.resume import ApplyExtractedResumeRequest, ResumeRead
from app.services.resume_service import (
    ResumeNotFoundError,
    ResumeValidationError,
    apply_extracted_to_profile,
    delete_resume,
    list_user_resumes,
    serialize_resume,
    set_preferred_resume,
    upload_resume,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeRead])
def get_resumes(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ResumeRead]:
    """List all resumes uploaded by the authenticated user."""
    return [ResumeRead.model_validate(serialize_resume(r)) for r in list_user_resumes(db, current_user)]


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
def create_resume(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    label: str | None = Form(default=None),
) -> ResumeRead:
    """Upload and parse a PDF or DOCX resume into isolated per-user storage."""
    try:
        resume = upload_resume(
            db,
            current_user,
            file,
            label=label,
            ip_address=get_client_ip(request),
        )
    except ResumeValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ResumeRead.model_validate(serialize_resume(resume))


@router.post("/{resume_id}/prefer", response_model=ResumeRead)
def mark_preferred_resume(
    resume_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResumeRead:
    """Set a resume as the user's preferred application resume."""
    try:
        resume = set_preferred_resume(db, current_user, resume_id, ip_address=get_client_ip(request))
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResumeRead.model_validate(serialize_resume(resume))


@router.post("/{resume_id}/apply-extracted", response_model=ProfileRead)
def apply_extracted_resume_fields(
    resume_id: str,
    payload: ApplyExtractedResumeRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProfileRead:
    """Apply user-reviewed extracted hints from a resume into the user's profile."""
    try:
        profile = apply_extracted_to_profile(
            db,
            current_user,
            resume_id,
            payload.fields_to_apply,
            payload.mark_as_verified,
            ip_address=get_client_ip(request),
        )
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProfileRead.model_validate(profile)


@router.delete("/{resume_id}", response_model=MessageResponse)
def remove_resume(
    resume_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """Delete a resume belonging to the authenticated user."""
    try:
        delete_resume(db, current_user, resume_id, ip_address=get_client_ip(request))
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MessageResponse(message="Resume deleted.")


"""User profile API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import ProfileRead, ProfileUpdateRequest
from app.services.profile_service import (
    ProfileValidationError,
    get_or_create_profile,
    update_profile,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
def read_profile(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProfileRead:
    """Return the authenticated user's profile (auto-initialized if missing)."""
    profile = get_or_create_profile(db, current_user)
    return ProfileRead.model_validate(profile)


@router.put("", response_model=ProfileRead)
def save_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProfileRead:
    """Update the authenticated user's profile fields."""
    try:
        profile = update_profile(
            db,
            current_user,
            payload,
            ip_address=get_client_ip(request),
        )
    except ProfileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ProfileRead.model_validate(profile)


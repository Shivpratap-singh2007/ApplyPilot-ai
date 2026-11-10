"""User profile management service with per-user isolation and field verification tracking."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile import UserProfile
from app.models.resume import Resume
from app.models.user import User
from app.schemas.profile import ProfileUpdateRequest
from app.services.audit_service import record_audit_event


class ProfileValidationError(ValueError):
    """Raised when profile update references invalid or unowned resources."""


def get_or_create_profile(db: Session, user: User) -> UserProfile:
    """Fetch the user's profile or initialize one seeded with verified account defaults."""
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is not None:
        return profile

    profile = UserProfile(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        verified_fields={"full_name": True, "email": True},
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(
    db: Session,
    user: User,
    payload: ProfileUpdateRequest,
    *,
    ip_address: str | None = None,
) -> UserProfile:
    """Update editable profile sections while preserving strict ownership and verification flags."""
    profile = get_or_create_profile(db, user)
    data = payload.model_dump(exclude_unset=True)
    explicit_verified = data.pop("verified_fields", None)

    if "preferred_resume_id" in data and data["preferred_resume_id"]:
        resume = db.scalar(
            select(Resume).where(
                Resume.id == data["preferred_resume_id"],
                Resume.user_id == user.id,
            )
        )
        if resume is None:
            raise ProfileValidationError("Selected preferred resume does not exist for this user.")

    verified_map = dict(profile.verified_fields or {})

    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(profile, key, value)
        if explicit_verified and key in explicit_verified:
            verified_map[key] = bool(explicit_verified[key])
        else:
            has_value = bool(value) if not isinstance(value, (list, dict)) else len(value) > 0
            verified_map[key] = has_value

    if explicit_verified:
        for key, flag in explicit_verified.items():
            verified_map[key] = bool(flag)

    profile.verified_fields = verified_map
    db.add(profile)
    record_audit_event(
        db,
        event_type="profile.updated",
        user_id=user.id,
        resource_type="user_profile",
        resource_id=profile.id,
        ip_address=ip_address,
        details={"updated_keys": sorted(data.keys())},
        commit=False,
    )
    db.commit()
    db.refresh(profile)
    return profile


"""Authentication and user account service."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit_service import record_audit_event

# Precomputed valid Argon2id hash used to equalize verification timing on unknown emails.
_DUMMY_HASH = hash_password("ApplyPilot-Dummy-Timing-Guard-99!")


class EmailAlreadyExistsError(Exception):
    """Raised when registering with an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials fail verification."""


class InactiveAccountError(Exception):
    """Raised when an inactive user attempts to authenticate."""


def register_user(db: Session, payload: RegisterRequest, ip_address: str | None = None) -> User:
    """Create a new user account and record a registration audit event."""
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise EmailAlreadyExistsError("An account with this email already exists.")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyExistsError("An account with this email already exists.") from exc

    db.add(Subscription(user_id=user.id, plan_code="free_local", status="active"))

    record_audit_event(
        db,
        event_type="auth.register",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip_address,
        details={"email": user.email},
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest, ip_address: str | None = None) -> User:
    """Verify user credentials and log success or failure."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        record_audit_event(
            db,
            event_type="auth.login.failed",
            user_id=None,
            resource_type="user",
            ip_address=ip_address,
            details={"reason": "unknown_email", "email": payload.email},
        )
        raise InvalidCredentialsError("Invalid email or password.")

    if not verify_password(payload.password, user.hashed_password):
        record_audit_event(
            db,
            event_type="auth.login.failed",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            details={"reason": "invalid_password"},
        )
        raise InvalidCredentialsError("Invalid email or password.")

    if not user.is_active:
        record_audit_event(
            db,
            event_type="auth.login.blocked",
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            details={"reason": "inactive_account"},
        )
        raise InactiveAccountError("This account is inactive.")

    record_audit_event(
        db,
        event_type="auth.login.success",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=ip_address,
    )
    return user


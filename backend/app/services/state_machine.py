"""Explicit 15-state application lifecycle state machine with persistence and guardrails."""

from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStateTransition

TERMINAL_STATES: frozenset[str] = frozenset({"SUBMITTED", "CANCELLED"})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "CREATED": frozenset({"VALIDATING_URL", "FAILED", "CANCELLED"}),
    "VALIDATING_URL": frozenset({"OPENING_PAGE", "FAILED", "CANCELLED"}),
    "OPENING_PAGE": frozenset({"ANALYZING_FORM", "WAITING_FOR_USER_INPUT", "FAILED", "CANCELLED"}),
    "ANALYZING_FORM": frozenset({"MATCHING_PROFILE", "WAITING_FOR_USER_INPUT", "FAILED", "CANCELLED"}),
    "MATCHING_PROFILE": frozenset({"FILLING_DRAFT", "WAITING_FOR_USER_INPUT", "FAILED", "CANCELLED"}),
    "FILLING_DRAFT": frozenset({"WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT", "FAILED", "CANCELLED"}),
    "WAITING_FOR_USER_INPUT": frozenset({"VALIDATING_URL", "WAITING_FOR_REVIEW", "APPROVED", "FAILED", "CANCELLED"}),
    "WAITING_FOR_REVIEW": frozenset({"APPROVED", "VALIDATING_URL", "FAILED", "CANCELLED"}),
    "APPROVED": frozenset({"SUBMITTING", "WAITING_FOR_REVIEW", "CANCELLED"}),
    "SUBMITTING": frozenset({"VERIFYING", "WAITING_FOR_USER_INPUT", "WAITING_FOR_REVIEW", "FAILED", "UNKNOWN"}),
    "VERIFYING": frozenset({"SUBMITTED", "FAILED", "UNKNOWN"}),
    # Safe retry from FAILED goes back through VALIDATING_URL / WAITING_FOR_REVIEW, never straight to SUBMITTING.
    "FAILED": frozenset({"VALIDATING_URL", "WAITING_FOR_REVIEW", "CANCELLED"}),
    # UNKNOWN must NOT auto-retry submission directly; user must manually cancel or re-inspect if verified safe.
    "UNKNOWN": frozenset({"CANCELLED"}),
    "SUBMITTED": frozenset(),
    "CANCELLED": frozenset(),
}


class InvalidStateTransitionError(ValueError):
    """Raised when an application attempts an unauthorized lifecycle transition."""


def transition_application_state(
    db: Session,
    application: Application,
    to_status: str,
    *,
    reason: str = "",
    commit: bool = True,
) -> Application:
    """Validate, apply, and persist an application state transition."""
    current = application.status
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if to_status not in allowed:
        raise InvalidStateTransitionError(
            f"Unauthorized transition from '{current}' to '{to_status}'."
        )

    application.status = to_status
    transition = ApplicationStateTransition(
        application_id=application.id,
        from_status=current,
        to_status=to_status,
        reason=reason[:500],
    )
    db.add(application)
    db.add(transition)
    if commit:
        db.commit()
        db.refresh(application)
    return application


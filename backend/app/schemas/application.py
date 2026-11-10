"""Pydantic schemas for application orchestration, review, approval, and tracking."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "CREATED",
    "VALIDATING_URL",
    "OPENING_PAGE",
    "ANALYZING_FORM",
    "MATCHING_PROFILE",
    "FILLING_DRAFT",
    "WAITING_FOR_USER_INPUT",
    "WAITING_FOR_REVIEW",
    "APPROVED",
    "SUBMITTING",
    "VERIFYING",
    "SUBMITTED",
    "FAILED",
    "UNKNOWN",
    "CANCELLED",
]


class ApplicationCreateRequest(BaseModel):
    """Request to inspect and draft-fill a new application URL."""

    model_config = ConfigDict(extra="forbid")

    target_url: str = Field(min_length=8, max_length=2048)
    application_type: Literal["internship", "job", "scholarship", "hackathon"] = "internship"
    title: str | None = Field(default=None, max_length=300)
    company_or_org: str | None = Field(default=None, max_length=300)
    resume_id: str | None = Field(default=None, max_length=36)
    run_immediately: bool = False


class ApplicationDraftUpdateRequest(BaseModel):
    """Updates proposed draft values or attached resume (invalidates prior approvals)."""

    model_config = ConfigDict(extra="forbid")

    edited_values: dict[str, str] = Field(default_factory=dict)
    resume_id: str | None = Field(default=None, max_length=36)
    title: str | None = Field(default=None, max_length=300)
    company_or_org: str | None = Field(default=None, max_length=300)


class ManualCompleteRequest(BaseModel):
    """Records a user-completed manual submission when automation is unsupported or CAPTCHA-gated."""

    model_config = ConfigDict(extra="forbid")

    confirmed_manually: bool = Field(default=True)
    confirmation_reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)


class ApprovalSnapshotRead(BaseModel):
    """Immutable snapshot summary tied to an approved application."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    target_url: str
    resume_id: str | None
    resume_sha256: str | None
    approved_values_json: dict[str, str]
    form_structure_hash: str
    snapshot_hash: str
    is_consumed: bool
    approved_at: datetime
    consumed_at: datetime | None


class StateTransitionRead(BaseModel):
    """State transition timeline entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    from_status: str | None
    to_status: str
    reason: str
    created_at: datetime


class ApplicationRead(BaseModel):
    """Full application detail view for progress, review, and history screens."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    resume_id: str | None
    target_url: str
    application_type: str
    title: str | None
    company_or_org: str | None
    status: str
    detected_fields_json: list[dict[str, Any]]
    draft_matches_json: list[dict[str, Any]]
    edited_values_json: dict[str, str]
    validation_warnings_json: list[str]
    missing_fields_json: list[str]
    has_draft_screenshot: bool = False
    has_confirmation_screenshot: bool = False
    confirmation_reference: str | None
    confirmation_evidence_json: dict[str, Any] | None
    error_message: str | None
    ai_provider_used: str | None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    transitions: list[StateTransitionRead] = Field(default_factory=list)
    latest_approval: ApprovalSnapshotRead | None = None


class ApplicationStatsRead(BaseModel):
    """Dashboard summary counts grouped by application lifecycle bucket."""

    total: int
    drafts: int
    awaiting_review: int
    submitted: int
    failed: int
    unknown: int
    cancelled: int


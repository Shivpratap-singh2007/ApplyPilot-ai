"""Application workflow, approval snapshot, and state transition ORM models."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    """Tracked internship, job, scholarship, or hackathon application."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resume_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    application_type: Mapped[str] = mapped_column(String(40), default="internship", nullable=False)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    company_or_org: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="CREATED", index=True, nullable=False)

    detected_fields_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    draft_matches_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    edited_values_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    validation_warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_fields_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    draft_screenshot_rel_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confirmation_screenshot_rel_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confirmation_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confirmation_evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    allow_localhost: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalSnapshot(Base):
    """Immutable cryptographic snapshot binding user approval to reviewed form state."""

    __tablename__ = "approval_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    resume_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resume_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_values_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    form_structure_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplicationStateTransition(Base):
    """Persistent state machine transition history per application."""

    __tablename__ = "application_state_transitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )


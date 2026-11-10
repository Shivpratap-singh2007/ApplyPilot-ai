"""User profile ORM model covering personal, education, professional, preferences, and hackathon data."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserProfile(Base):
    """Comprehensive, verified personal application profile owned strictly by one user."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Personal information
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(400), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Education
    college: Mapped[str | None] = mapped_column(String(240), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(120), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(160), nullable=True)
    current_semester: Mapped[str | None] = mapped_column(String(60), nullable=True)
    graduation_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cgpa: Mapped[str | None] = mapped_column(String(30), nullable=True)
    school_education: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Professional information
    technical_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    programming_languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    projects: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    work_experience: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    internships: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    certifications: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    achievements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Application preferences
    preferred_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_locations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    work_mode_preference: Mapped[str | None] = mapped_column(String(40), nullable=True)
    internship_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    availability: Mapped[str | None] = mapped_column(String(160), nullable=True)
    preferred_resume_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Hackathon information
    team_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    team_members: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hackathon_project_idea: Mapped[str | None] = mapped_column(Text, nullable=True)
    hackathon_tech_stack: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hackathon_repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hackathon_project_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tracks whether each profile key was explicitly verified by the user
    verified_fields: Mapped[dict[str, bool]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


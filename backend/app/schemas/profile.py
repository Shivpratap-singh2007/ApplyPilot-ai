"""Pydantic schemas for comprehensive user profile management."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdateRequest(BaseModel):
    """Editable user profile fields across personal, academic, professional, preferences, and hackathon sections."""

    model_config = ConfigDict(extra="forbid")

    # Personal information
    full_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=400)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=40)

    # Education
    college: str | None = Field(default=None, max_length=240)
    degree: str | None = Field(default=None, max_length=120)
    branch: str | None = Field(default=None, max_length=160)
    current_semester: str | None = Field(default=None, max_length=60)
    graduation_year: str | None = Field(default=None, max_length=20)
    cgpa: str | None = Field(default=None, max_length=30)
    school_education: dict[str, Any] = Field(default_factory=dict)

    # Professional information
    technical_skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    work_experience: list[dict[str, Any]] = Field(default_factory=list)
    internships: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    github_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)

    # Application preferences
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    work_mode_preference: Literal["remote", "onsite", "hybrid", "any", ""] | None = None
    internship_duration: str | None = Field(default=None, max_length=100)
    availability: str | None = Field(default=None, max_length=160)
    preferred_resume_id: str | None = Field(default=None, max_length=36)

    # Hackathon information
    team_name: str | None = Field(default=None, max_length=160)
    team_members: list[str] = Field(default_factory=list)
    hackathon_project_idea: str | None = Field(default=None, max_length=2000)
    hackathon_tech_stack: list[str] = Field(default_factory=list)
    hackathon_repo_url: str | None = Field(default=None, max_length=500)
    hackathon_project_description: str | None = Field(default=None, max_length=4000)

    verified_fields: dict[str, bool] | None = None


class ProfileRead(BaseModel):
    """Serialized user profile with explicit verification indicators."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    full_name: str | None
    email: str | None
    phone: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    postal_code: str | None
    college: str | None
    degree: str | None
    branch: str | None
    current_semester: str | None
    graduation_year: str | None
    cgpa: str | None
    school_education: dict[str, Any]
    technical_skills: list[str]
    programming_languages: list[str]
    projects: list[dict[str, Any]]
    work_experience: list[dict[str, Any]]
    internships: list[dict[str, Any]]
    certifications: list[dict[str, Any]]
    achievements: list[str]
    github_url: str | None
    linkedin_url: str | None
    portfolio_url: str | None
    preferred_roles: list[str]
    preferred_locations: list[str]
    work_mode_preference: str | None
    internship_duration: str | None
    availability: str | None
    preferred_resume_id: str | None
    team_name: str | None
    team_members: list[str]
    hackathon_project_idea: str | None
    hackathon_tech_stack: list[str]
    hackathon_repo_url: str | None
    hackathon_project_description: str | None
    verified_fields: dict[str, bool]
    created_at: datetime
    updated_at: datetime


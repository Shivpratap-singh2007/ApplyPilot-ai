"""Structured schemas for form fields, verified user profiles, and AI matching outputs."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileContext(BaseModel):
    """Sanitized, verified user profile subset eligible for form matching (no secrets/tokens)."""

    model_config = ConfigDict(extra="ignore")

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None

    college: str | None = None
    degree: str | None = None
    branch: str | None = None
    current_semester: str | None = None
    graduation_year: str | None = None
    cgpa: str | None = None

    technical_skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    preferred_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    work_mode_preference: str | None = None
    availability: str | None = None
    internship_duration: str | None = None

    projects_summary: str | None = None
    experience_summary: str | None = None
    certifications_summary: str | None = None
    achievements_summary: str | None = None

    team_name: str | None = None
    hackathon_project_idea: str | None = None
    hackathon_tech_stack: list[str] = Field(default_factory=list)
    hackathon_repo_url: str | None = None

    approved_resume_path: str | None = None


ALLOWED_PROFILE_KEYS: frozenset[str] = frozenset(ProfileContext.model_fields.keys())


class FormFieldDescriptor(BaseModel):
    """Normalized representation of a single form control extracted from the DOM."""

    field_id: str
    tag: Literal["input", "textarea", "select", "radio_group", "checkbox"]
    input_type: str = "text"
    name: str = ""
    element_id: str = ""
    label: str = ""
    placeholder: str = ""
    nearby_text: str = ""
    required: bool = False
    options: list[str] = Field(default_factory=list)
    selector: str = ""
    current_value: str = ""


class FieldMatchResult(BaseModel):
    """
    Structured mapping output for a form field.

    Note: `confidence_score` is a heuristic indicator (0.0 to 1.0),
    not a calibrated statistical probability.
    """

    model_config = ConfigDict(extra="forbid")

    field_id: str
    suggested_profile_key: str | None = None
    proposed_value: str = ""
    confidence_score: float = Field(ge=0.0, le=1.0)
    source: Literal["deterministic", "semantic", "ollama", "unmatched"]
    reason: str
    requires_human_review: bool = True
    missing_profile_data: bool = False
    is_ai_draft: bool = False


class FormAnalysisOutput(BaseModel):
    """Complete matching result for an inspected application form."""

    url: str
    page_title: str = ""
    has_captcha_or_challenge: bool = False
    challenge_reason: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    matches: list[FieldMatchResult] = Field(default_factory=list)
    ai_provider_used: str = "deterministic_only"
    ai_warnings: list[str] = Field(default_factory=list)


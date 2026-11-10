"""Bridge between backend database models and the modular local AI + Playwright agent package."""

import sys

from app.core.config import REPO_ROOT, get_settings
from app.models.profile import UserProfile
from app.models.resume import Resume
from app.models.user import User
from app.services.resume_service import resolve_resume_abs_path

AGENT_ROOT = REPO_ROOT / "agent"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from applypilot_agent.ai import OllamaProvider, ProfileContext  # noqa: E402
from applypilot_agent.browser import (  # noqa: E402
    PlaywrightDraftWorker,
    UnsafeURLError,
    compute_form_structure_hash,
    validate_target_url,
)


def _format_summary(items: list[dict], primary_key: str) -> str | None:
    parts = [str(item.get(primary_key) or "").strip() for item in items if isinstance(item, dict)]
    joined = "; ".join(p for p in parts if p)
    return joined or None


def build_profile_context(profile: UserProfile, resume: Resume | None = None) -> ProfileContext:
    """Construct a sanitized ProfileContext strictly from verified/user-owned data."""
    approved_resume_path: str | None = None
    if resume is not None:
        abs_path = resolve_resume_abs_path(resume)
        if abs_path.is_file():
            approved_resume_path = str(abs_path)

    return ProfileContext(
        full_name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        address=profile.address,
        city=profile.city,
        state=profile.state,
        country=profile.country,
        postal_code=profile.postal_code,
        college=profile.college,
        degree=profile.degree,
        branch=profile.branch,
        current_semester=profile.current_semester,
        graduation_year=profile.graduation_year,
        cgpa=profile.cgpa,
        technical_skills=list(profile.technical_skills or []),
        programming_languages=list(profile.programming_languages or []),
        github_url=profile.github_url,
        linkedin_url=profile.linkedin_url,
        portfolio_url=profile.portfolio_url,
        preferred_roles=list(profile.preferred_roles or []),
        preferred_locations=list(profile.preferred_locations or []),
        work_mode_preference=profile.work_mode_preference,
        availability=profile.availability,
        internship_duration=profile.internship_duration,
        projects_summary=_format_summary(profile.projects or [], "title"),
        experience_summary=_format_summary(profile.work_experience or [], "role"),
        certifications_summary=_format_summary(profile.certifications or [], "name"),
        achievements_summary="; ".join(profile.achievements or []) or None,
        team_name=profile.team_name,
        hackathon_project_idea=profile.hackathon_project_idea,
        hackathon_tech_stack=list(profile.hackathon_tech_stack or []),
        hackathon_repo_url=profile.hackathon_repo_url,
        approved_resume_path=approved_resume_path,
    )


def create_ollama_provider(user: User | None = None) -> OllamaProvider:
    """Instantiate configured local Ollama provider with optional per-user model selection."""
    settings = get_settings()
    model = (user.preferred_ollama_model if user and user.preferred_ollama_model else None) or settings.ollama_model
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=model,
        fallback_model=settings.ollama_fallback_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        num_ctx=settings.ollama_num_ctx,
        temperature=settings.ollama_temperature,
    )


def create_playwright_worker() -> PlaywrightDraftWorker:
    """Instantiate bounded Playwright automation worker from settings."""
    settings = get_settings()
    return PlaywrightDraftWorker(
        headless=settings.playwright_headless,
        timeout_ms=settings.playwright_timeout_ms,
        max_concurrent_contexts=settings.playwright_max_concurrent_contexts,
    )


__all__ = [
    "UnsafeURLError",
    "build_profile_context",
    "compute_form_structure_hash",
    "create_ollama_provider",
    "create_playwright_worker",
    "validate_target_url",
]


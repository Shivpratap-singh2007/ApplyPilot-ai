"""Deterministic Python rule engine executed before any local LLM inference."""

from dataclasses import dataclass
import re

from applypilot_agent.ai.schemas import FieldMatchResult, FormFieldDescriptor, ProfileContext


@dataclass(frozen=True)
class _Rule:
    profile_key: str
    patterns: tuple[re.Pattern[str], ...]
    confidence: float = 0.95
    needs_review: bool = False


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


_FIELD_RULES: tuple[_Rule, ...] = (
    _Rule("email", (_rx(r"\b(e-?mail|email\s*address)\b"),), confidence=0.98),
    _Rule("phone", (_rx(r"\b(phone|mobile|contact\s*number|tel(ephone)?)\b"),), confidence=0.96),
    _Rule("full_name", (_rx(r"\b(full\s*name|your\s*name|applicant\s*name|candidate\s*name|^name$)\b"),), confidence=0.96),
    _Rule("linkedin_url", (_rx(r"\b(linkedin|linked\s*in)\b"),), confidence=0.97),
    _Rule("github_url", (_rx(r"\b(github|git\s*hub)\b"),), confidence=0.97),
    _Rule("portfolio_url", (_rx(r"\b(portfolio|personal\s*website|website\s*url)\b"),), confidence=0.93),
    _Rule("college", (_rx(r"\b(college|university|institution|school\s*name)\b"),), confidence=0.94),
    _Rule("degree", (_rx(r"\b(degree|qualification|program)\b"),), confidence=0.92),
    _Rule("branch", (_rx(r"\b(branch|major|specialization|department|stream|field\s*of\s*study)\b"),), confidence=0.92),
    _Rule("current_semester", (_rx(r"\b(semester|current\s*sem)\b"),), confidence=0.92),
    _Rule("graduation_year", (_rx(r"\b(graduation\s*year|passing\s*year|expected\s*graduation|grad\s*year)\b"),), confidence=0.94),
    _Rule("cgpa", (_rx(r"\b(cgpa|gpa|percentage|grade)\b"),), confidence=0.91),
    _Rule("city", (_rx(r"\b(city|town)\b"),), confidence=0.93),
    _Rule("state", (_rx(r"\b(state|province|region)\b"),), confidence=0.91),
    _Rule("country", (_rx(r"\b(country|nation)\b"),), confidence=0.93),
    _Rule("postal_code", (_rx(r"\b(postal\s*code|zip\s*code|pin\s*code)\b"),), confidence=0.94),
    _Rule("address", (_rx(r"\b(street\s*address|mailing\s*address|home\s*address|^address$)\b"),), confidence=0.90),
    _Rule("technical_skills", (_rx(r"\b(technical\s*skills|key\s*skills|^skills$)\b"),), confidence=0.90),
    _Rule("programming_languages", (_rx(r"\b(programming\s*languages|languages\s*known)\b"),), confidence=0.91),
    _Rule("work_mode_preference", (_rx(r"\b(remote|onsite|hybrid|work\s*mode|work\s*preference)\b"),), confidence=0.88, needs_review=True),
    _Rule("availability", (_rx(r"\b(availability|start\s*date|when\s*can\s*you\s*start|joining)\b"),), confidence=0.88, needs_review=True),
    _Rule("internship_duration", (_rx(r"\b(duration|internship\s*length|months\s*available)\b"),), confidence=0.88, needs_review=True),
    _Rule("team_name", (_rx(r"\b(team\s*name)\b"),), confidence=0.93),
    _Rule("hackathon_repo_url", (_rx(r"\b(repo(sitory)?\s*url|project\s*github)\b"),), confidence=0.92),
)


def _format_profile_value(profile: ProfileContext, key: str) -> str:
    raw = getattr(profile, key, None)
    if raw is None:
        return ""
    if isinstance(raw, list):
        return ", ".join(str(item).strip() for item in raw if str(item).strip())
    return str(raw).strip()


def _best_select_option(options: list[str], target_value: str) -> str:
    """Match a profile value against select/radio options case-insensitively."""
    if not options or not target_value:
        return target_value
    target_lower = target_value.strip().lower()
    for opt in options:
        if opt.strip().lower() == target_lower:
            return opt
    for opt in options:
        opt_lower = opt.strip().lower()
        if opt_lower and (target_lower in opt_lower or opt_lower in target_lower):
            return opt
    return ""


def match_field_deterministically(
    field: FormFieldDescriptor,
    profile: ProfileContext,
) -> FieldMatchResult | None:
    """
    Attempt deterministic rule-based matching for standard fields.

    Returns None when the field is ambiguous or open-ended and should be
    forwarded to the local LLM (or flagged for human input).
    """
    if field.input_type == "file":
        haystack = " ".join([field.label, field.name, field.element_id, field.nearby_text]).lower()
        if any(token in haystack for token in ("resume", "cv", "curriculum")):
            resume_path = (profile.approved_resume_path or "").strip()
            if resume_path:
                return FieldMatchResult(
                    field_id=field.field_id,
                    suggested_profile_key="approved_resume_path",
                    proposed_value=resume_path,
                    confidence_score=0.98,
                    source="deterministic",
                    reason="Matched resume file upload input to user's approved resume.",
                    requires_human_review=False,
                    missing_profile_data=False,
                )
            return FieldMatchResult(
                field_id=field.field_id,
                suggested_profile_key="approved_resume_path",
                proposed_value="",
                confidence_score=0.95,
                source="deterministic",
                reason="Resume upload field detected, but no approved resume is selected in profile.",
                requires_human_review=True,
                missing_profile_data=True,
            )
        return None

    # Open-ended descriptive textareas should be drafted/reviewed rather than blindly mapped
    if field.tag == "textarea":
        return None

    candidate_text = " ".join(
        part.strip()
        for part in [field.label, field.name, field.element_id, field.placeholder]
        if part and part.strip()
    )
    if not candidate_text:
        return None

    # First name / last name split support
    lowered = candidate_text.lower()
    if re.search(r"\b(first\s*name|given\s*name)\b", lowered):
        parts = (profile.full_name or "").strip().split()
        val = parts[0] if parts else ""
        return FieldMatchResult(
            field_id=field.field_id,
            suggested_profile_key="full_name",
            proposed_value=val,
            confidence_score=0.94 if val else 0.90,
            source="deterministic",
            reason="Extracted first name token from verified full name."
            if val
            else "First name field matched, but full name is missing from profile.",
            requires_human_review=not bool(val),
            missing_profile_data=not bool(val),
        )
    if re.search(r"\b(last\s*name|family\s*name|surname)\b", lowered):
        parts = (profile.full_name or "").strip().split()
        val = " ".join(parts[1:]) if len(parts) > 1 else ""
        return FieldMatchResult(
            field_id=field.field_id,
            suggested_profile_key="full_name",
            proposed_value=val,
            confidence_score=0.93 if val else 0.85,
            source="deterministic",
            reason="Extracted last name token from verified full name."
            if val
            else "Last name field matched, but surname could not be derived from profile.",
            requires_human_review=not bool(val),
            missing_profile_data=not bool(val),
        )

    for rule in _FIELD_RULES:
        if any(pattern.search(candidate_text) for pattern in rule.patterns):
            raw_value = _format_profile_value(profile, rule.profile_key)
            if not raw_value:
                return FieldMatchResult(
                    field_id=field.field_id,
                    suggested_profile_key=rule.profile_key,
                    proposed_value="",
                    confidence_score=rule.confidence,
                    source="deterministic",
                    reason=f"Matched field to '{rule.profile_key}', but verified profile value is missing.",
                    requires_human_review=True,
                    missing_profile_data=True,
                )

            final_value = raw_value
            needs_review = rule.needs_review
            if field.tag in {"select", "radio_group"} and field.options:
                matched_option = _best_select_option(field.options, raw_value)
                if matched_option:
                    final_value = matched_option
                else:
                    final_value = ""
                    needs_review = True
                    return FieldMatchResult(
                        field_id=field.field_id,
                        suggested_profile_key=rule.profile_key,
                        proposed_value="",
                        confidence_score=0.55,
                        source="deterministic",
                        reason=f"Matched '{rule.profile_key}', but value '{raw_value}' did not match available options.",
                        requires_human_review=True,
                        missing_profile_data=False,
                    )

            return FieldMatchResult(
                field_id=field.field_id,
                suggested_profile_key=rule.profile_key,
                proposed_value=final_value,
                confidence_score=rule.confidence,
                source="deterministic",
                reason=f"Deterministic label/attribute match to verified profile '{rule.profile_key}'.",
                requires_human_review=needs_review,
                missing_profile_data=False,
            )

    return None


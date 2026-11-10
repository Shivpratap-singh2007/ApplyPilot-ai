"""Lightweight local semantic matching module (zero external ML weights, low-RAM friendly)."""

from collections import Counter
import math
import re

from applypilot_agent.ai.deterministic_matcher import _best_select_option, _format_profile_value
from applypilot_agent.ai.schemas import FieldMatchResult, FormFieldDescriptor, ProfileContext

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Canonical descriptor phrases for semantic cosine similarity when regex rules miss phrasing variations.
_PROFILE_KEY_PROTOTYPES: dict[str, tuple[str, ...]] = {
    "full_name": ("candidate legal name", "applicant full name", "student name"),
    "email": ("contact email id", "university email address", "primary email"),
    "phone": ("mobile contact number", "whatsapp phone number", "cell number"),
    "college": ("educational institution", "current university or institute", "alma mater school"),
    "degree": ("academic degree program", "bachelor master qualification"),
    "branch": ("academic major specialization", "engineering stream discipline", "course concentration"),
    "graduation_year": ("expected year of passing", "cohort completion year", "class of year"),
    "cgpa": ("cumulative grade point average", "academic score percentage marks"),
    "technical_skills": ("core competencies frameworks tools", "relevant technical expertise"),
    "programming_languages": ("coding languages proficiency", "software languages known"),
    "github_url": ("source code profile link", "github handle url"),
    "linkedin_url": ("professional network profile link", "linkedin account url"),
    "portfolio_url": ("personal showcase website", "online portfolio projects link"),
    "city": ("current city of residence", "hometown location"),
    "country": ("country of residence", "home nation"),
    "work_mode_preference": ("preferred working arrangement remote hybrid office", "location mode"),
    "availability": ("earliest joining date", "notice period or start availability"),
    "internship_duration": ("number of months available for internship", "preferred stint duration"),
    "team_name": ("hackathon squad name", "group name"),
    "hackathon_repo_url": ("hackathon project source repository", "team codebase url"),
}


def _vectorize(text: str) -> Counter[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    grams: list[str] = list(tokens)
    grams.extend(f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1))
    return Counter(grams)


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


_PRECOMPUTED_VECTORS: dict[str, list[Counter[str]]] = {
    key: [_vectorize(phrase) for phrase in phrases]
    for key, phrases in _PROFILE_KEY_PROTOTYPES.items()
}


def match_field_semantically(
    field: FormFieldDescriptor,
    profile: ProfileContext,
    *,
    threshold: float = 0.55,
) -> FieldMatchResult | None:
    """
    Attempt lightweight token/bigram cosine similarity against canonical profile descriptions.

    Skips textareas and file inputs so open-ended questions still route to the LLM or user input.
    """
    if field.tag == "textarea" or field.input_type == "file":
        return None

    descriptor_text = " ".join(
        part.strip()
        for part in [field.label, field.placeholder, field.nearby_text, field.name]
        if part and part.strip()
    )
    if not descriptor_text:
        return None

    field_vec = _vectorize(descriptor_text)
    best_key: str | None = None
    best_score = 0.0

    for key, proto_vecs in _PRECOMPUTED_VECTORS.items():
        score = max(_cosine(field_vec, pv) for pv in proto_vecs)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key is None or best_score < threshold:
        return None

    raw_val = _format_profile_value(profile, best_key)
    if not raw_val:
        return FieldMatchResult(
            field_id=field.field_id,
            suggested_profile_key=best_key,
            proposed_value="",
            confidence_score=round(min(best_score, 0.80), 3),
            source="semantic",
            reason=f"Semantic similarity matched '{best_key}', but verified profile value is missing.",
            requires_human_review=True,
            missing_profile_data=True,
        )

    final_val = raw_val
    if field.tag in {"select", "radio_group"} and field.options:
        final_val = _best_select_option(field.options, raw_val)

    return FieldMatchResult(
        field_id=field.field_id,
        suggested_profile_key=best_key,
        proposed_value=final_val,
        confidence_score=round(min(best_score, 0.85), 3),
        source="semantic",
        reason=f"Semantic token similarity matched field to '{best_key}' (review recommended).",
        requires_human_review=True,
        missing_profile_data=not bool(final_val),
    )


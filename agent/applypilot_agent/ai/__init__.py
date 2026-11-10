"""Local AI matching and Ollama provider package."""

from applypilot_agent.ai.deterministic_matcher import match_field_deterministically
from applypilot_agent.ai.provider import AIProvider, OllamaProvider, analyze_fields_hybrid, sanitize_untrusted_text
from applypilot_agent.ai.schemas import (
    ALLOWED_PROFILE_KEYS,
    FieldMatchResult,
    FormAnalysisOutput,
    FormFieldDescriptor,
    ProfileContext,
)
from applypilot_agent.ai.semantic_matcher import match_field_semantically

__all__ = [
    "ALLOWED_PROFILE_KEYS",
    "AIProvider",
    "FieldMatchResult",
    "FormAnalysisOutput",
    "FormFieldDescriptor",
    "OllamaProvider",
    "ProfileContext",
    "analyze_fields_hybrid",
    "match_field_deterministically",
    "match_field_semantically",
    "sanitize_untrusted_text",
]


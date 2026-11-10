"""Pydantic schemas for user settings, usage summary, and privacy controls."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SettingsRead(BaseModel):
    """User-facing local AI and SaaS quota configuration."""

    preferred_ollama_model: str | None
    default_ollama_model: str
    fallback_ollama_model: str
    ollama_base_url: str
    allow_localhost_automation: bool
    plan_tier: str
    usage_summary: dict[str, int]


class SettingsUpdateRequest(BaseModel):
    """Editable user AI/model preferences."""

    model_config = ConfigDict(extra="forbid")

    preferred_ollama_model: str | None = Field(default=None, max_length=120)


class AuditLogRead(BaseModel):
    """User-scoped audit log record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    details_json: dict[str, Any]
    created_at: datetime


class AccountDeleteRequest(BaseModel):
    """Explicit password-confirmed request to permanently delete user data."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)
    confirm_phrase: str = Field(min_length=1, max_length=32)


"""Pydantic schemas for resume upload, extraction, and verification."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResumeRead(BaseModel):
    """Resume record exposed to its owning user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    label: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    sha256_hash: str
    extracted_text: str
    extracted_data_json: dict[str, Any]
    is_verified: bool
    is_preferred: bool
    created_at: datetime


class ApplyExtractedResumeRequest(BaseModel):
    """Applies selected extracted resume suggestions to the user's profile."""

    model_config = ConfigDict(extra="forbid")

    fields_to_apply: list[str] = Field(default_factory=list)
    mark_as_verified: bool = True


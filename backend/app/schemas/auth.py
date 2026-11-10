"""Pydantic schemas for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_strength


class RegisterRequest(BaseModel):
    """Request body for registering a new user account."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        """Trim outer whitespace and reject empty names."""
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normalize email addresses to lowercase."""
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        """Validate password complexity requirements."""
        validate_password_strength(value)
        return value


class LoginRequest(BaseModel):
    """Request body for user login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Normalize email addresses to lowercase."""
        return str(value).strip().lower()


class UserRead(BaseModel):
    """Publicly safe representation of the authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    """Authentication response returning session metadata and safe user info."""

    access_token: str
    token_type: str = "bearer"
    csrf_token: str
    user: UserRead


class MessageResponse(BaseModel):
    """Simple operational status message."""

    message: str


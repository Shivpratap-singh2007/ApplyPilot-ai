"""Pydantic schemas for health and readiness checks."""

from typing import Literal

from pydantic import BaseModel


class OllamaHealth(BaseModel):
    """Local Ollama server status reported by the health endpoint."""

    provider: str
    base_url: str
    configured_model: str
    fallback_model: str
    status: Literal["reachable", "unreachable"]
    model_available: bool
    available_models: list[str]
    detail: str | None = None


class HealthResponse(BaseModel):
    """Overall service health payload."""

    status: Literal["ok", "degraded"]
    app_name: str
    environment: str
    database: Literal["ok", "error"]
    ollama: OllamaHealth


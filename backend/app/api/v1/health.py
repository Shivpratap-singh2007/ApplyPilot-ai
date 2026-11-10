"""Health and readiness check endpoints."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.application import Application
from app.models.user import User
from app.schemas.health import HealthResponse, OllamaHealth

router = APIRouter(tags=["health"])
_START_TIME = time.monotonic()


def _check_ollama() -> OllamaHealth:
    """Inspect local Ollama daemon availability and pulled models with short timeouts."""
    settings = get_settings()
    base_url = settings.ollama_base_url.rstrip("/")
    try:
        timeout = httpx.Timeout(1.5, connect=1.0)
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [
                str(item.get("name"))
                for item in data.get("models", [])
                if isinstance(item, dict) and item.get("name")
            ]
            configured = settings.ollama_model
            fallback = settings.ollama_fallback_model
            model_available = any(
                m == configured or m.startswith(f"{configured}:") or m == fallback or m.startswith(f"{fallback}:")
                for m in models
            )
            return OllamaHealth(
                provider=settings.ai_provider,
                base_url=base_url,
                configured_model=configured,
                fallback_model=fallback,
                status="reachable",
                model_available=model_available,
                available_models=models,
                detail=None if model_available else f"Ollama is running, but {configured} is not pulled yet.",
            )
    except Exception as exc:
        return OllamaHealth(
            provider=settings.ai_provider,
            base_url=base_url,
            configured_model=settings.ollama_model,
            fallback_model=settings.ollama_fallback_model,
            status="unreachable",
            model_available=False,
            available_models=[],
            detail=f"Local Ollama unavailable: {type(exc).__name__}",
        )


@router.get("/health", response_model=HealthResponse)
def health_check(response: Response, db: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    """Report backend, database, and local Ollama availability."""
    settings = get_settings()
    db_status: str = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    ollama = _check_ollama()
    overall = "ok" if db_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,  # type: ignore[arg-type]
        app_name=settings.app_name,
        environment=settings.app_env,
        database=db_status,  # type: ignore[arg-type]
        ollama=ollama,
    )


@router.get("/metrics")
def monitoring_metrics(db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    """Return non-PII aggregate operational metrics for monitoring."""
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_apps = db.scalar(select(func.count(Application.id))) or 0
    submitted_apps = db.scalar(
        select(func.count(Application.id)).where(Application.status == "SUBMITTED")
    ) or 0
    failed_apps = db.scalar(
        select(func.count(Application.id)).where(Application.status == "FAILED")
    ) or 0
    unknown_apps = db.scalar(
        select(func.count(Application.id)).where(Application.status == "UNKNOWN")
    ) or 0
    return {
        "uptime_seconds": round(time.monotonic() - _START_TIME, 2),
        "users_total": int(total_users),
        "applications_total": int(total_apps),
        "applications_submitted": int(submitted_apps),
        "applications_failed": int(failed_apps),
        "applications_unknown": int(unknown_apps),
    }

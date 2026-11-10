"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repository root regardless of whether backend runs from repo root or backend/.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
INSECURE_DEFAULT_SECRET = "dev-only-change-this-secret-key-before-any-shared-deployment"


class Settings(BaseSettings):
    """Central typed settings for ApplyPilot AI backend."""

    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE) if DEFAULT_ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "ApplyPilot AI"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"

    secret_key: str = INSECURE_DEFAULT_SECRET
    data_encryption_key: str | None = None
    access_token_expire_minutes: int = 60
    session_cookie_name: str = "applypilot_session"
    csrf_cookie_name: str = "applypilot_csrf"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_rate_limit_requests: int = 20
    auth_rate_limit_window_seconds: int = 60

    allowed_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = f"sqlite:///{(REPO_ROOT / 'data' / 'applypilot.db').as_posix()}"

    data_dir: Path = REPO_ROOT / "data"
    upload_dir: Path = REPO_ROOT / "data" / "uploads"
    screenshot_dir: Path = REPO_ROOT / "data" / "screenshots"
    max_upload_mb: int = 10

    ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_fallback_model: str = "qwen3:1.7b"
    ollama_timeout_seconds: int = 120
    ollama_num_ctx: int = 2048
    ollama_temperature: float = 0.1

    playwright_headless: bool = True
    playwright_max_concurrent_contexts: int = 2
    playwright_timeout_ms: int = 20000
    allow_localhost_automation: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_relative_sqlite_path(cls, value: str) -> str:
        """Anchor relative sqlite:///./... URLs to the repository root."""
        if isinstance(value, str) and value.startswith("sqlite:///./"):
            rel_part = value.removeprefix("sqlite:///./")
            return f"sqlite:///{(REPO_ROOT / rel_part).as_posix()}"
        return value

    @field_validator("data_dir", "upload_dir", "screenshot_dir", mode="before")
    @classmethod
    def resolve_relative_dir(cls, value: str | Path) -> Path:
        """Resolve relative directory settings against the repository root."""
        path = Path(value)
        if not path.is_absolute():
            return (REPO_ROOT / path).resolve()
        return path

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Reject insecure defaults when running in production mode."""
        if self.app_env == "production":
            if self.secret_key == INSECURE_DEFAULT_SECRET or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be set to a strong >=32 char random secret in production.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production.")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a clean list."""
        return [origin.strip() for origin in self.allowed_cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        """Return True if the configured database uses SQLite."""
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


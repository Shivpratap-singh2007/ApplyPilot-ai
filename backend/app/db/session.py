"""Database engine and session management (SQLite local MVP + PostgreSQL compatible)."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Ensure the parent folder exists for file-backed SQLite databases."""
    if not database_url.startswith("sqlite:///"):
        return
    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path in {"", ":memory:"} or raw_path.startswith("file::memory:"):
        return
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create a configured SQLAlchemy engine for SQLite or PostgreSQL."""
    settings = get_settings()
    url = database_url or settings.database_url
    is_sqlite = url.startswith("sqlite")
    _ensure_sqlite_parent_dir(url)

    connect_args: dict[str, Any] = {"check_same_thread": False} if is_sqlite else {}
    engine_kwargs: dict[str, Any] = {
        "connect_args": connect_args,
        "pool_pre_ping": True,
        "future": True,
    }
    engine = create_engine(url, **engine_kwargs)

    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            if ":memory:" not in url:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


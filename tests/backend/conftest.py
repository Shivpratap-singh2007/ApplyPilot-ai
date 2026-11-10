"""Pytest fixtures for ApplyPilot AI backend tests."""

from collections.abc import Generator
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
TESTS_ROOT = Path(__file__).resolve().parents[2] / "tests"
for p in (BACKEND_ROOT, TESTS_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.core.config import get_settings  # noqa: E402
from app.core.security import auth_rate_limiter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Isolate filesystem storage, settings cache, and rate limiters per test."""
    auth_rate_limiter.reset()
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SCREENSHOT_DIR", str(tmp_path / "screenshots"))
    monkeypatch.setenv("ALLOW_LOCALHOST_AUTOMATION", "false")
    get_settings.cache_clear()
    yield
    auth_rate_limiter.reset()
    get_settings.cache_clear()


@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    """Provide an isolated SQLite database session per test."""
    db_path = tmp_path / "test_applypilot.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient wired to the isolated test database."""
    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client

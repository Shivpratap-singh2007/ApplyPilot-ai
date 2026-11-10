"""Phase 8 readiness tests: PostgreSQL Alembic DDL compatibility, subscriptions, and monitoring metrics."""

from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription


def test_alembic_generates_valid_postgresql_ddl() -> None:
    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    buf = StringIO()
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", "postgresql+psycopg://applypilot:pass@localhost:5432/applypilot")
    cfg.output_buffer = buf

    command.upgrade(cfg, "head", sql=True)
    ddl = buf.getvalue()
    assert "CREATE TABLE users" in ddl
    assert "CREATE TABLE user_profiles" in ddl
    assert "CREATE TABLE approval_snapshots" in ddl
    assert "CREATE TABLE subscriptions" in ddl


def test_subscription_auto_provisioned_and_metrics_endpoint(
    client: TestClient, db_session: Session
) -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "saas@example.com", "full_name": "SaaS User", "password": "StrongPassword123!"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]

    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == user_id))
    assert sub is not None
    assert sub.plan_code == "free_local"
    assert sub.status == "active"

    metrics = client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert "x-process-time-ms" in metrics.headers
    payload = metrics.json()
    assert payload["users_total"] >= 1
    assert "uptime_seconds" in payload


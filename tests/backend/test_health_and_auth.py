"""Phase 1 tests for health endpoint, authentication, CSRF protection, rate limiting, and audit logs."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audit import AuditLog


def test_health_endpoint_reports_database_ok_and_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["ollama"]["provider"] == "ollama"
    assert data["ollama"]["status"] in {"reachable", "unreachable"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_register_login_me_and_audit_trail(client: TestClient, db_session: Session) -> None:
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Ada.Lovelace@Example.com",
            "full_name": "Ada Lovelace",
            "password": "StrongPassword123!",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["user"]["email"] == "ada.lovelace@example.com"
    assert "hashed_password" not in reg_data["user"]
    assert "password" not in reg_data["user"]
    token = reg_data["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["full_name"] == "Ada Lovelace"

    dup_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ada.lovelace@example.com",
            "full_name": "Ada Duplicate",
            "password": "StrongPassword123!",
        },
    )
    assert dup_resp.status_code == 409

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ada.lovelace@example.com", "password": "StrongPassword123!"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["email"] == "ada.lovelace@example.com"

    events = list(db_session.scalars(select(AuditLog.event_type).order_by(AuditLog.created_at)))
    assert "auth.register" in events
    assert "auth.login.success" in events


def test_rejects_weak_password_extra_fields_and_tampered_jwt(client: TestClient) -> None:
    weak_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "full_name": "Weak User", "password": "onlyletters"},
    )
    assert weak_resp.status_code == 422

    extra_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "extra@example.com",
            "full_name": "Extra User",
            "password": "StrongPassword123!",
            "is_admin": True,
        },
    )
    assert extra_resp.status_code == 422

    unauth_resp = client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

    tampered_resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert tampered_resp.status_code == 401


def test_cookie_auth_enforces_csrf_on_mutations(client: TestClient) -> None:
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cookieuser@example.com",
            "full_name": "Cookie User",
            "password": "StrongPassword123!",
        },
    )
    assert reg_resp.status_code == 201
    csrf_token = reg_resp.json()["csrf_token"]

    # GET works via HttpOnly cookie without CSRF header
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200

    # Unsafe POST via cookie without X-CSRF-Token must be blocked
    blocked_logout = client.post("/api/v1/auth/logout")
    assert blocked_logout.status_code == 403

    # With matching X-CSRF-Token, logout succeeds and clears session
    ok_logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert ok_logout.status_code == 200

    after_logout = client.get("/api/v1/auth/me")
    assert after_logout.status_code == 401


def test_login_rate_limiting_and_failed_login_audit(client: TestClient, db_session: Session) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "ratelimit@example.com",
            "full_name": "Rate Limit User",
            "password": "StrongPassword123!",
        },
    )
    limit = get_settings().auth_rate_limit_requests
    for _ in range(limit):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit@example.com", "password": "WrongPassword123!"},
        )
        assert resp.status_code == 401

    throttled = client.post(
        "/api/v1/auth/login",
        json={"email": "ratelimit@example.com", "password": "WrongPassword123!"},
    )
    assert throttled.status_code == 429
    assert "retry-after" in throttled.headers

    failed_events = list(
        db_session.scalars(select(AuditLog).where(AuditLog.event_type == "auth.login.failed"))
    )
    assert len(failed_events) == limit


"""Tests for Phase 2 profile management, resume validation/extraction, isolation, and privacy controls."""

from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from pypdf import PdfWriter
import pytest

from app.core.config import get_settings
from app.models.resume import Resume
from sqlalchemy import select
from sqlalchemy.orm import Session


def _register_and_headers(client: TestClient, email: str, name: str = "Test User") -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": name, "password": "StrongPassword123!"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_docx_bytes(lines: list[str]) -> bytes:
    doc = DocxDocument()
    for line in lines:
        doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_profile_crud_and_verification_tracking(client: TestClient) -> None:
    headers = _register_and_headers(client, "profile@example.com", "Ada Lovelace")

    get_resp = client.get("/api/v1/profile", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Ada Lovelace"
    assert get_resp.json()["verified_fields"]["email"] is True

    put_resp = client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "phone": "+91-9988776655",
            "college": "National Tech University",
            "degree": "B.Tech",
            "branch": "Computer Science",
            "graduation_year": "2027",
            "cgpa": "9.1",
            "technical_skills": ["FastAPI", "Playwright", "Docker"],
            "programming_languages": ["Python", "TypeScript"],
            "github_url": "https://github.com/adalovelace",
            "linkedin_url": "https://linkedin.com/in/adalovelace",
            "work_mode_preference": "remote",
            "team_name": "Engine Builders",
            "hackathon_project_idea": "Local-first form assistant",
        },
    )
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["college"] == "National Tech University"
    assert data["verified_fields"]["college"] is True
    assert data["team_name"] == "Engine Builders"


def test_resume_upload_validation_docx_extraction_and_user_isolation(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers_a = _register_and_headers(client, "usera@example.com", "User A")
    headers_b = _register_and_headers(client, "userb@example.com", "User B")

    # Reject disallowed extension
    bad_ext = client.post(
        "/api/v1/resumes",
        headers=headers_a,
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
    )
    assert bad_ext.status_code == 400

    # Reject spoofed PDF without %PDF- signature
    bad_sig = client.post(
        "/api/v1/resumes",
        headers=headers_a,
        files={"file": ("fake.pdf", b"not a real pdf", "application/pdf")},
    )
    assert bad_sig.status_code == 400

    # Reject oversized upload
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    too_big = client.post(
        "/api/v1/resumes",
        headers=headers_a,
        files={"file": ("big.pdf", b"%PDF-" + (b"0" * (1024 * 1024 + 50)), "application/pdf")},
    )
    assert too_big.status_code == 400

    # Valid DOCX upload + extraction
    docx_bytes = _make_docx_bytes(
        [
            "User A",
            "Email: usera.dev@example.com | Phone: +91 9876543210",
            "B.Tech Computer Science, 2027, CGPA: 8.9",
            "GitHub: https://github.com/usera-dev",
            "Skills: Python, TypeScript, FastAPI, Docker, Playwright",
        ]
    )
    up_docx = client.post(
        "/api/v1/resumes",
        headers=headers_a,
        data={"label": "SWE DOCX Resume"},
        files={
            "file": (
                "../../traversal.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert up_docx.status_code == 201
    resume_a = up_docx.json()
    assert resume_a["is_preferred"] is True
    assert resume_a["extracted_data_json"]["github_url"] == "https://github.com/usera-dev"
    assert "Python" in resume_a["extracted_data_json"]["programming_languages"]
    assert "FastAPI" in resume_a["extracted_data_json"]["technical_skills"]
    assert "User A" in resume_a["extracted_text"]

    # Verify extracted_text is stored encrypted at rest in the database
    stored_row = db_session.scalar(select(Resume).where(Resume.id == resume_a["id"]))
    assert stored_row is not None
    assert stored_row.extracted_text.startswith("enc:v1:")
    assert "User A" not in stored_row.extracted_text

    # Valid PDF upload (second resume)
    up_pdf = client.post(
        "/api/v1/resumes",
        headers=headers_a,
        data={"label": "Blank Valid PDF"},
        files={"file": ("resume.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert up_pdf.status_code == 201
    resume_pdf = up_pdf.json()
    assert resume_pdf["is_preferred"] is False

    # Apply extracted hints to User A's profile with explicit verification
    apply_resp = client.post(
        f"/api/v1/resumes/{resume_a['id']}/apply-extracted",
        headers=headers_a,
        json={"fields_to_apply": ["github_url", "technical_skills"], "mark_as_verified": True},
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json()["github_url"] == "https://github.com/usera-dev"
    assert apply_resp.json()["verified_fields"]["github_url"] is True

    # User B isolation checks
    assert client.get("/api/v1/resumes", headers=headers_b).json() == []
    assert client.delete(f"/api/v1/resumes/{resume_a['id']}", headers=headers_b).status_code == 404
    assert client.post(f"/api/v1/resumes/{resume_a['id']}/prefer", headers=headers_b).status_code == 404

    # User A sets second resume preferred and deletes first
    pref_resp = client.post(f"/api/v1/resumes/{resume_pdf['id']}/prefer", headers=headers_a)
    assert pref_resp.status_code == 200
    assert pref_resp.json()["is_preferred"] is True

    del_resp = client.delete(f"/api/v1/resumes/{resume_a['id']}", headers=headers_a)
    assert del_resp.status_code == 200


def test_settings_privacy_export_and_account_deletion(client: TestClient) -> None:
    headers = _register_and_headers(client, "privacy@example.com", "Grace Hopper")

    # Upload a resume so we verify file cleanup on account deletion
    up = client.post(
        "/api/v1/resumes",
        headers=headers,
        files={"file": ("grace.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert up.status_code == 201
    user_upload_dir = get_settings().upload_dir / up.json()["user_id"]
    assert user_upload_dir.is_dir()

    # Update preferred Ollama model in settings
    set_resp = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"preferred_ollama_model": "qwen3:1.7b"},
    )
    assert set_resp.status_code == 200
    assert set_resp.json()["preferred_ollama_model"] == "qwen3:1.7b"

    # Export data
    export_resp = client.get("/api/v1/privacy/export", headers=headers)
    assert export_resp.status_code == 200
    exported = export_resp.json()
    assert exported["account"]["email"] == "privacy@example.com"
    assert "hashed_password" not in exported["account"]
    assert len(exported["resumes"]) == 1

    # Audit logs scoped to user
    logs_resp = client.get("/api/v1/privacy/audit-logs", headers=headers)
    assert logs_resp.status_code == 200
    assert any(item["event_type"] == "privacy.data_exported" for item in logs_resp.json())

    # Wrong password rejected for account deletion
    bad_del = client.post(
        "/api/v1/privacy/delete-account",
        headers=headers,
        json={"password": "WrongPassword1!", "confirm_phrase": "DELETE"},
    )
    assert bad_del.status_code == 400

    # Valid deletion purges DB and local files
    ok_del = client.post(
        "/api/v1/privacy/delete-account",
        headers=headers,
        json={"password": "StrongPassword123!", "confirm_phrase": "DELETE"},
    )
    assert ok_del.status_code == 200
    assert not user_upload_dir.exists()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


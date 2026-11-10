"""End-to-end backend + Playwright workflow, approval enforcement, security, and failure tests."""

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
import pytest

from app.core.config import get_settings
from test_sites.internship_server import LocalInternshipServer


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _setup_full_user(client: TestClient, email: str = "applicant@example.com") -> tuple[dict[str, str], str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Ada Lovelace", "password": "StrongPassword123!"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    up = client.post(
        "/api/v1/resumes",
        headers=headers,
        data={"label": "Primary Resume"},
        files={"file": ("ada_resume.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert up.status_code == 201
    resume_id = up.json()["id"]

    prof = client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "full_name": "Ada Lovelace",
            "email": email,
            "phone": "+91-9876543210",
            "college": "Analytical Institute of Technology",
            "degree": "B.Tech",
            "branch": "Computer Science",
            "graduation_year": "2027",
            "cgpa": "9.3",
            "technical_skills": ["Python", "FastAPI", "Playwright"],
            "github_url": "https://github.com/ada",
            "linkedin_url": "https://linkedin.com/in/ada",
            "portfolio_url": "https://ada.dev",
            "work_mode_preference": "remote",
            "team_name": "Difference Engine",
            "hackathon_repo_url": "https://github.com/ada/engine",
            "preferred_resume_id": resume_id,
        },
    )
    assert prof.status_code == 200
    return headers, resume_id


def test_api_blocks_localhost_and_unsafe_urls_by_default(client: TestClient) -> None:
    headers, _ = _setup_full_user(client, "urlsec@example.com")
    for bad_url in (
        "http://127.0.0.1:8000/api/v1/health",
        "http://169.254.169.254/latest/meta-data/",
        "file:///C:/Windows/win.ini",
    ):
        resp = client.post(
            "/api/v1/applications",
            headers=headers,
            json={"target_url": bad_url, "application_type": "internship"},
        )
        assert resp.status_code == 400


def test_full_internship_e2e_approval_invalidation_and_duplicate_prevention(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALLOW_LOCALHOST_AUTOMATION", "true")
    get_settings.cache_clear()

    headers_a, _resume_id = _setup_full_user(client, "e2ea@example.com")
    headers_b, _ = _setup_full_user(client, "e2eb@example.com")

    with LocalInternshipServer() as server:
        # 1. Start application inspection & draft fill (no submission!)
        create_resp = client.post(
            "/api/v1/applications",
            headers=headers_a,
            json={
                "target_url": f"{server.base_url}/internship",
                "application_type": "internship",
                "company_or_org": "Acme Cloud",
                "run_immediately": True,
            },
        )
        assert create_resp.status_code == 201
        app_data = create_resp.json()
        app_id = app_data["id"]
        assert server.submissions == []
        assert app_data["has_draft_screenshot"] is True

        # Cross-user isolation on application and screenshot
        assert client.get(f"/api/v1/applications/{app_id}", headers=headers_b).status_code == 404
        assert (
            client.get(f"/api/v1/applications/{app_id}/screenshots/draft", headers=headers_b).status_code
            == 404
        )
        assert (
            client.get(f"/api/v1/applications/{app_id}/screenshots/draft", headers=headers_a).status_code
            == 200
        )

        # 2. Cannot submit before explicit approval
        premature_submit = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers_a)
        assert premature_submit.status_code == 409
        assert server.submissions == []

        # 3. Cannot approve while required 'why_apply' is empty (even if AI drafted, clearing it blocks approval)
        clear_resp = client.patch(
            f"/api/v1/applications/{app_id}/draft",
            headers=headers_a,
            json={"edited_values": {"why_apply": ""}},
        )
        assert clear_resp.status_code == 200
        premature_approve = client.post(f"/api/v1/applications/{app_id}/approve", headers=headers_a)
        assert premature_approve.status_code == 422

        # 4. Fill descriptive answer and approve
        edit1 = client.patch(
            f"/api/v1/applications/{app_id}/draft",
            headers=headers_a,
            json={"edited_values": {"why_apply": "I enjoy building Python APIs and automation."}},
        )
        assert edit1.status_code == 200
        assert edit1.json()["status"] == "WAITING_FOR_REVIEW"

        approve1 = client.post(f"/api/v1/applications/{app_id}/approve", headers=headers_a)
        assert approve1.status_code == 200
        snap1_hash = approve1.json()["snapshot_hash"]

        # 5. Editing after approval MUST invalidate approval and block submission until re-approved
        edit2 = client.patch(
            f"/api/v1/applications/{app_id}/draft",
            headers=headers_a,
            json={"edited_values": {"why_apply": "Updated answer: excited to contribute to Acme Cloud backend systems."}},
        )
        assert edit2.status_code == 200
        assert edit2.json()["status"] == "WAITING_FOR_REVIEW"

        blocked_after_edit = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers_a)
        assert blocked_after_edit.status_code == 409
        assert server.submissions == []

        # 6. Re-approve and submit
        approve2 = client.post(f"/api/v1/applications/{app_id}/approve", headers=headers_a)
        assert approve2.status_code == 200
        assert approve2.json()["snapshot_hash"] != snap1_hash

        submit_resp = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers_a)
        assert submit_resp.status_code == 200
        submitted = submit_resp.json()
        assert submitted["status"] == "SUBMITTED"
        assert submitted["confirmation_reference"] == "AP-LOCAL-001"
        assert submitted["has_confirmation_screenshot"] is True
        assert len(server.submissions) == 1

        # 7. Duplicate submission attempt MUST be blocked
        dup_submit = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers_a)
        assert dup_submit.status_code == 409
        assert len(server.submissions) == 1

        # 8. Dashboard stats check
        stats = client.get("/api/v1/applications/stats", headers=headers_a).json()
        assert stats["total"] == 1
        assert stats["submitted"] == 1


@pytest.mark.parametrize(
    ("route", "app_type"),
    [
        ("/job", "job"),
        ("/hackathon", "hackathon"),
        ("/multistep", "scholarship"),
        ("/dynamic", "job"),
        ("/upload", "internship"),
    ],
)
def test_diverse_local_forms_draft_approve_and_submit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    app_type: str,
) -> None:
    monkeypatch.setenv("ALLOW_LOCALHOST_AUTOMATION", "true")
    get_settings.cache_clear()

    headers, _ = _setup_full_user(client, f"form_{app_type}_{route.strip('/')}@example.com")
    with LocalInternshipServer() as server:
        create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "target_url": f"{server.base_url}{route}",
                "application_type": app_type,
                "run_immediately": True,
            },
        )
        assert create.status_code == 201
        app_id = create.json()["id"]
        assert create.json()["status"] == "WAITING_FOR_REVIEW"
        assert server.submissions == []

        approve = client.post(f"/api/v1/applications/{app_id}/approve", headers=headers)
        assert approve.status_code == 200

        submit = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers)
        assert submit.status_code == 200
        assert submit.json()["status"] == "SUBMITTED"
        assert len(server.submissions) == 1


def test_failed_validation_and_unknown_outcome_and_missing_required_forms(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALLOW_LOCALHOST_AUTOMATION", "true")
    get_settings.cache_clear()

    headers, _ = _setup_full_user(client, "edgecases@example.com")
    with LocalInternshipServer() as server:
        # 1. Missing required field detection
        missing_resp = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "target_url": f"{server.base_url}/missing-required",
                "application_type": "scholarship",
                "run_immediately": True,
            },
        )
        assert missing_resp.status_code == 201
        assert missing_resp.json()["status"] == "WAITING_FOR_USER_INPUT"
        assert any("Sponsor Referral Code" in f for f in missing_resp.json()["missing_fields_json"])

        # 2. Failed submission due to server validation alert
        fail_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "target_url": f"{server.base_url}/validation-error",
                "application_type": "job",
                "run_immediately": True,
            },
        )
        fail_id = fail_create.json()["id"]
        assert client.post(f"/api/v1/applications/{fail_id}/approve", headers=headers).status_code == 200
        fail_submit = client.post(f"/api/v1/applications/{fail_id}/submit", headers=headers)
        assert fail_submit.status_code == 200
        assert fail_submit.json()["status"] == "FAILED"
        assert "failed server validation" in (fail_submit.json()["error_message"] or "").lower()

        # 3. Unknown submission status & no automatic retry
        unk_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "target_url": f"{server.base_url}/ambiguous-submit",
                "application_type": "job",
                "run_immediately": True,
            },
        )
        unk_id = unk_create.json()["id"]
        assert client.post(f"/api/v1/applications/{unk_id}/approve", headers=headers).status_code == 200
        unk_submit = client.post(f"/api/v1/applications/{unk_id}/submit", headers=headers)
        assert unk_submit.status_code == 200
        assert unk_submit.json()["status"] == "UNKNOWN"
        assert unk_submit.json()["submitted_at"] is None
        assert client.post(f"/api/v1/applications/{unk_id}/retry", headers=headers).status_code == 409
        assert client.post(f"/api/v1/applications/{unk_id}/submit", headers=headers).status_code == 409

        # 4. Manual-assisted completion fallback on CAPTCHA-paused form
        cap_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "target_url": f"{server.base_url}/captcha-form",
                "application_type": "internship",
                "run_immediately": True,
            },
        )
        cap_id = cap_create.json()["id"]
        assert cap_create.json()["status"] == "WAITING_FOR_USER_INPUT"
        manual_resp = client.post(
            f"/api/v1/applications/{cap_id}/manual-complete",
            headers=headers,
            json={
                "confirmed_manually": True,
                "confirmation_reference": "MANUAL-REF-77",
                "notes": "Solved CAPTCHA and submitted directly in browser.",
            },
        )
        assert manual_resp.status_code == 200
        assert manual_resp.json()["status"] == "SUBMITTED"
        assert manual_resp.json()["confirmation_reference"] == "MANUAL-REF-77"
        assert manual_resp.json()["confirmation_evidence_json"]["mode"] == "manual_assisted"
        # Duplicate manual-complete or submit must be blocked
        assert (
            client.post(
                f"/api/v1/applications/{cap_id}/manual-complete",
                headers=headers,
                json={"confirmed_manually": True},
            ).status_code
            == 409
        )


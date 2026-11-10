"""Real full-stack browser UI E2E test driving Next.js -> FastAPI -> Playwright -> LocalInternshipServer."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from playwright.sync_api import sync_playwright
import pytest

TESTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_ROOT.parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from test_sites.internship_server import LocalInternshipServer  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_http_ok(url: str, timeout_s: float = 25.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=5.0, trust_env=False)
            if r.status_code < 500:
                return
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Service at {url} did not become ready within {timeout_s}s.")


def _launch_browser(pw):
    try:
        return pw.chromium.launch(headless=True)
    except Exception:
        for ch in ("chrome", "msedge"):
            try:
                return pw.chromium.launch(headless=True, channel=ch)
            except Exception:
                continue
        raise


def test_full_browser_ui_signup_profile_resume_review_approve_submit(tmp_path: Path) -> None:
    next_build_id = REPO_ROOT / "frontend" / ".next" / "BUILD_ID"
    if not next_build_id.is_file():
        pytest.skip("Frontend production build (.next/BUILD_ID) not present.")

    backend_port = _free_port()
    frontend_port = _free_port()

    db_path = (tmp_path / "e2e.db").as_posix()
    backend_env = os.environ.copy()
    backend_env.update(
        {
            "PYTHONPATH": str(REPO_ROOT / "backend"),
            "DATABASE_URL": f"sqlite:///{db_path}",
            "DATA_DIR": str(tmp_path / "data"),
            "UPLOAD_DIR": str(tmp_path / "uploads"),
            "SCREENSHOT_DIR": str(tmp_path / "screenshots"),
            "ALLOW_LOCALHOST_AUTOMATION": "true",
            "ALLOWED_CORS_ORIGINS": f"http://localhost:{frontend_port},http://127.0.0.1:{frontend_port}",
        }
    )

    # Migrate isolated E2E SQLite database
    subprocess.run(
        [
            str(REPO_ROOT / ".venv" / "Scripts" / "python.exe"),
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        cwd=str(REPO_ROOT / "backend"),
        env=backend_env,
        check=True,
    )

    backend_log = tmp_path / "backend.log"
    frontend_log = tmp_path / "frontend.log"
    backend_log_fh = backend_log.open("w", encoding="utf-8")
    frontend_log_fh = frontend_log.open("w", encoding="utf-8")

    backend_proc = subprocess.Popen(
        [
            str(REPO_ROOT / ".venv" / "Scripts" / "python.exe"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(backend_port),
        ],
        cwd=str(REPO_ROOT / "backend"),
        env=backend_env,
        stdout=backend_log_fh,
        stderr=subprocess.STDOUT,
    )

    frontend_env = os.environ.copy()
    frontend_env["BACKEND_INTERNAL_URL"] = f"http://127.0.0.1:{backend_port}"
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "start", "--", "-p", str(frontend_port), "-H", "127.0.0.1"],
        cwd=str(REPO_ROOT / "frontend"),
        env=frontend_env,
        stdout=frontend_log_fh,
        stderr=subprocess.STDOUT,
    )

    resume_file = tmp_path / "e2e_resume.pdf"
    resume_file.write_bytes(
        b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >> endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer << /Size 4 /Root 1 0 R >>\nstartxref\n184\n%%EOF\n"
    )

    try:
        try:
            _wait_http_ok(f"http://127.0.0.1:{backend_port}/api/v1/health")
            _wait_http_ok(f"http://127.0.0.1:{frontend_port}/")
        except Exception as exc:
            backend_log_fh.flush()
            frontend_log_fh.flush()
            raise RuntimeError(
                f"{exc}\n--- backend.log ---\n{backend_log.read_text(errors='ignore')}\n"
                f"--- frontend.log ---\n{frontend_log.read_text(errors='ignore')}"
            ) from exc

        frontend_base = f"http://127.0.0.1:{frontend_port}"

        with LocalInternshipServer() as test_site, sync_playwright() as pw:
            browser = _launch_browser(pw)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(20000)

            # 1. Sign up in real UI
            page.goto(f"{frontend_base}/signup")
            page.get_by_label("Full name").fill("Ada Lovelace")
            page.get_by_label("Email address").fill("ada.ui@example.com")
            page.get_by_label("Password").fill("StrongPassword123!")
            page.get_by_role("button", name="Create account").click()
            page.wait_for_url(f"{frontend_base}/dashboard")

            # 2. Upload resume in Resume Manager UI
            page.goto(f"{frontend_base}/resumes")
            page.get_by_label("Resume Label").fill("E2E Resume")
            page.locator("#resume-file").set_input_files(str(resume_file))
            page.get_by_role("button", name="Upload & Extract").click()
            page.get_by_text("E2E Resume").wait_for()

            # 3. Fill profile in My Profile UI
            page.goto(f"{frontend_base}/profile")
            page.get_by_label("Phone Number").fill("+91-9876543210")
            page.get_by_label("College / University").fill("Analytical University")
            page.get_by_label("Degree").fill("B.Tech")
            page.get_by_role("button", name="Save Verified Profile").click()
            page.get_by_text("Profile saved and verified.").wait_for()

            # 4. Submit new application URL -> Agent Progress -> Review
            page.goto(f"{frontend_base}/applications/new")
            page.get_by_label("Application URL *").fill(f"{test_site.base_url}/internship")
            page.get_by_role("button", name="Inspect & Draft Form").click()

            # Progress auto-redirects to /review on WAITING_FOR_REVIEW (when Ollama drafts why_apply)
            # or exposes "Proceed to Review" on /progress on WAITING_FOR_USER_INPUT.
            page.wait_for_url(lambda u: "/progress" in u or "/review" in u, timeout=20000)
            deadline = time.monotonic() + 75.0
            while time.monotonic() < deadline:
                if "/review" in page.url:
                    break
                proceed_link = page.get_by_role("link", name="Proceed to Review")
                if proceed_link.count() > 0 and proceed_link.is_visible():
                    assert test_site.submissions == []
                    proceed_link.click()
                    page.wait_for_url("**/review", timeout=15000)
                    break
                page.wait_for_timeout(400)
            else:
                raise AssertionError(f"Did not reach review screen within 75s; current URL: {page.url}")
            assert test_site.submissions == []

            # 5. Fill/refine required textarea in Review UI and explicitly Approve and Submit
            page.locator("#review-why_apply").wait_for(timeout=15000)
            page.locator("#review-why_apply").fill("I build Python automation and FastAPI applications.")
            page.get_by_role("button", name="Approve and Submit").click()

            page.wait_for_url(lambda u: "/applications/" in u and not u.endswith("/review") and not u.endswith("/progress"))
            page.get_by_text("SUBMITTED").first.wait_for(timeout=20000)
            page.get_by_text("AP-LOCAL-001").first.wait_for()
            assert len(test_site.submissions) == 1

            context.close()
            browser.close()
    finally:
        frontend_proc.terminate()
        backend_proc.terminate()
        frontend_proc.wait(timeout=5)
        backend_proc.wait(timeout=5)
        backend_log_fh.close()
        frontend_log_fh.close()


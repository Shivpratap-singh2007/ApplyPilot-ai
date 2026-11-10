"""Playwright integration tests against locally hosted internship and CAPTCHA test forms."""

from pathlib import Path
import sys

AGENT_ROOT = Path(__file__).resolve().parents[2] / "agent"
TESTS_ROOT = Path(__file__).resolve().parents[2] / "tests"
for p in (AGENT_ROOT, TESTS_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from applypilot_agent.ai import OllamaProvider, ProfileContext  # noqa: E402
from applypilot_agent.browser import PlaywrightDraftWorker  # noqa: E402
from test_sites.internship_server import LocalInternshipServer  # noqa: E402


def _write_minimal_pdf(target: Path) -> Path:
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >> endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer << /Size 4 /Root 1 0 R >>\nstartxref\n184\n%%EOF\n"
    )
    target.write_bytes(pdf_bytes)
    return target


def test_playwright_fills_local_internship_draft_without_submitting(tmp_path: Path) -> None:
    resume_file = _write_minimal_pdf(tmp_path / "ada_resume.pdf")
    screenshot_file = tmp_path / "draft_preview.png"

    profile = ProfileContext(
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone="+91-9876543210",
        college="Analytical Institute of Technology",
        degree="B.Tech",
        branch="Computer Science",
        graduation_year="2027",
        linkedin_url="https://linkedin.com/in/ada-lovelace",
        github_url="https://github.com/ada-lovelace",
        work_mode_preference="Remote",
        projects_summary="Built local-first Python automation and REST services.",
        approved_resume_path=str(resume_file),
    )

    worker = PlaywrightDraftWorker(headless=True)
    ollama = OllamaProvider()  # Uses live local Ollama if running; degrades safely if offline

    with LocalInternshipServer() as server:
        result = worker.inspect_and_fill_draft(
            url=f"{server.base_url}/internship",
            profile=profile,
            ai_provider=ollama,
            screenshot_path=screenshot_file,
            allow_localhost=True,
        )

        # Critical rule: NEVER submit automatically!
        assert result.submitted is False
        assert server.submissions == []

    assert screenshot_file.is_file()
    assert screenshot_file.stat().st_size > 1000
    assert "full_name" in result.filled_field_ids
    assert "email" in result.filled_field_ids
    assert "college" in result.filled_field_ids
    assert "degree" in result.filled_field_ids
    assert "resume" in result.filled_field_ids
    assert result.status in {"WAITING_FOR_REVIEW", "WAITING_FOR_USER_INPUT"}


def test_playwright_pauses_when_captcha_detected(tmp_path: Path) -> None:
    profile = ProfileContext(full_name="Ada Lovelace", email="ada@example.com")
    worker = PlaywrightDraftWorker(headless=True)

    with LocalInternshipServer() as server:
        result = worker.inspect_and_fill_draft(
            url=f"{server.base_url}/captcha-form",
            profile=profile,
            screenshot_path=tmp_path / "captcha.png",
            allow_localhost=True,
        )
        assert result.submitted is False
        assert server.submissions == []

    assert result.status == "WAITING_FOR_USER_INPUT"
    assert result.challenge_reason is not None
    assert "CAPTCHA" in result.challenge_reason


def test_playwright_sanitizes_malicious_dom_before_ollama(tmp_path: Path) -> None:
    import json
    import httpx

    captured_prompts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}]})
        if request.url.path == "/api/chat":
            captured_prompts.append(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "proposals": [
                                    {
                                        "field_id": "custom_q",
                                        "suggested_profile_key": None,
                                        "proposed_value": "",
                                        "confidence_score": 0.2,
                                        "reason": "Ignored untrusted prompt injection instruction.",
                                        "requires_human_review": True,
                                        "is_ai_draft": True,
                                    }
                                ]
                            }
                        ),
                    }
                },
            )
        return httpx.Response(404)

    profile = ProfileContext(full_name="Ada Lovelace", email="ada@example.com")
    worker = PlaywrightDraftWorker(headless=True)
    provider = OllamaProvider(transport=httpx.MockTransport(handler))

    with LocalInternshipServer() as server:
        result = worker.inspect_and_fill_draft(
            url=f"{server.base_url}/prompt-injection",
            profile=profile,
            ai_provider=provider,
            screenshot_path=tmp_path / "inj.png",
            allow_localhost=True,
        )
        assert result.submitted is False
        assert server.submissions == []

    assert len(captured_prompts) == 1
    assert "Ignore previous instructions" not in captured_prompts[0]
    assert "[FILTERED_UNTRUSTED_TEXT]" in captured_prompts[0]


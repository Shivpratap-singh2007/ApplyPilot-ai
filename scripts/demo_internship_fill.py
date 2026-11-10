"""Standalone demonstration: inspect and draft-fill a local internship application form."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agent"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from applypilot_agent.ai import OllamaProvider, ProfileContext  # noqa: E402
from applypilot_agent.browser import PlaywrightDraftWorker  # noqa: E402
from test_sites.internship_server import LocalInternshipServer  # noqa: E402


def main() -> None:
    demo_dir = REPO_ROOT / "data" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    resume_path = demo_dir / "sample_resume.pdf"
    if not resume_path.exists():
        resume_path.write_bytes(b"%PDF-1.4\n% ApplyPilot demo resume\n%%EOF\n")

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
        projects_summary="Built local automation tools with Python, FastAPI, and Playwright.",
        approved_resume_path=str(resume_path),
    )

    worker = PlaywrightDraftWorker(headless=True)
    ollama = OllamaProvider()
    screenshot_path = REPO_ROOT / "data" / "screenshots" / "demo_internship_draft.png"

    with LocalInternshipServer() as server:
        result = worker.inspect_and_fill_draft(
            url=f"{server.base_url}/internship",
            profile=profile,
            ai_provider=ollama,
            screenshot_path=screenshot_path,
            allow_localhost=True,
        )
        print(result.model_dump_json(indent=2))
        print(f"Server submissions count (must be 0): {len(server.submissions)}")


if __name__ == "__main__":
    main()


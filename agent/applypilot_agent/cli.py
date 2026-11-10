"""Standalone CLI entrypoint for running ApplyPilot's non-submitting browser worker."""

import argparse
from pathlib import Path
import sys

AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from applypilot_agent.ai import OllamaProvider, ProfileContext  # noqa: E402
from applypilot_agent.browser import PlaywrightDraftWorker  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and draft-fill an application URL without submitting.")
    parser.add_argument("url", help="Target application URL")
    parser.add_argument("--name", default="", help="Verified full name")
    parser.add_argument("--email", default="", help="Verified email")
    parser.add_argument("--college", default="", help="Verified college/university")
    parser.add_argument("--resume", default=None, help="Path to approved resume PDF/DOCX")
    parser.add_argument("--screenshot", default="data/screenshots/worker_cli_draft.png", help="Screenshot output path")
    parser.add_argument("--model", default="qwen3:4b", help="Local Ollama model name")
    parser.add_argument("--allow-localhost", action="store_true", help="Allow localhost URLs for local testing")
    args = parser.parse_args()

    profile = ProfileContext(
        full_name=args.name or None,
        email=args.email or None,
        college=args.college or None,
        approved_resume_path=args.resume,
    )
    worker = PlaywrightDraftWorker(headless=True)
    provider = OllamaProvider(model=args.model)
    result = worker.inspect_and_fill_draft(
        url=args.url,
        profile=profile,
        ai_provider=provider,
        screenshot_path=Path(args.screenshot),
        allow_localhost=args.allow_localhost,
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()


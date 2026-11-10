# ApplyPilot AI

Local-first AI-powered internship, job, scholarship, and hackathon application assistant powered by **Ollama (Qwen3 4B)**, **FastAPI**, **Next.js**, and **Playwright**.

> **Zero Paid Cloud LLMs** — All AI inference runs locally via `http://localhost:11434`.
> **Explicit Human Approval** — Applications are inspected, drafted, and verified against an immutable approval snapshot before submission.

## Project Structure

```text
ApplyPilot-ai/
├── frontend/      # Next.js + TypeScript + Tailwind CSS UI (13 complete pages)
├── backend/       # FastAPI + SQLAlchemy 2.0 + Alembic API & orchestration server
├── agent/         # Local Ollama AI provider & Playwright automation engine
├── tests/         # Pytest unit/integration/security/E2E suites & local test forms
├── docs/          # Architecture, security model, and limitations docs
├── scripts/       # Windows PowerShell helper scripts & local demo script
├── .env.example   # Environment variable template
└── README.md
```

## Prerequisites (Windows 10/11)

- Python 3.12 (`.venv` at repo root)
- Node.js 20+ (verified with Node `v24.19.0` / npm `11.17.0`)
- [Ollama](https://ollama.com/download) installed locally (`ollama pull qwen3:4b`, or `ollama pull qwen3:1.7b` for low-RAM machines)
- Google Chrome, Microsoft Edge, or Playwright Chromium (`.\.venv\Scripts\python.exe -m playwright install chromium`)

## Local Setup

1. Copy environment config:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Create and populate the Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
   .\.venv\Scripts\python.exe -m pip install -r agent\requirements.txt
   ```
3. Run database migrations:
   ```powershell
   .\scripts\migrate.ps1
   ```
4. Install frontend dependencies:
   ```powershell
   npm --prefix frontend install
   ```
5. Start backend and frontend in separate terminals:
   ```powershell
   .\scripts\start-backend.ps1
   .\scripts\start-frontend.ps1
   ```
6. (Optional) Start local test forms server for safe manual testing (`ALLOW_LOCALHOST_AUTOMATION=true` required in `.env` for localhost test mode):
   ```powershell
   .\scripts\start-test-sites.ps1
   ```

## Running Tests

```powershell
# Full backend, security, and Playwright E2E test suites (33 tests)
.\.venv\Scripts\python.exe -m pytest tests\backend tests\agent -v

# Frontend unit tests, TypeScript typecheck, and production build
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

See [architecture.md](docs/architecture.md) and [security-and-limitations.md](docs/security-and-limitations.md) for security model details, PostgreSQL migration notes, and limitations.

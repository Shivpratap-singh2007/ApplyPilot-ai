# ApplyPilot AI Architecture

ApplyPilot AI is structured as a modular monorepo:

- `frontend/`: Next.js 15 (TypeScript, Tailwind CSS) UI covering Landing, Signup, Login, Dashboard, My Profile, Resume Manager, New Application, Agent Progress, Application Review, Application History, Application Details, Settings, and Privacy Controls with dark/light themes.
- `backend/`: FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic backend with Argon2id auth, JWT + HttpOnly cookies, CSRF verification, rate limiting, profile & resume extraction services, 15-state application state machine, immutable approval snapshots, SaaS usage tracking, and audit logs.
- `agent/`: Local AI provider abstraction (`OllamaProvider` targeting `qwen3:4b` with `qwen3:1.7b` fallback), deterministic rule engine, prompt-injection defenses, URL/SSRF/DNS-rebinding validator, and Playwright multi-step DOM inspector/filler/submitter.
- `tests/`: Pytest backend, agent, security, and Playwright E2E suites plus `tests/test_sites/internship_server.py` hosting all 9 local test form scenarios.
- `scripts/`: PowerShell startup/migration/test-site scripts and standalone Playwright demo script.

## Non-Negotiable Principles

1. **Local-First AI**: Zero paid cloud LLM APIs. All LLM inference uses local Ollama at `http://localhost:11434`.
2. **Deterministic First**: Common fields are matched deterministically in Python before invoking local LLM inference.
3. **Zero Fabrication**: Missing profile facts stay empty and are flagged for user input.
4. **Explicit Human Approval**: Submissions require an explicit user-approved cryptographic snapshot (`ApprovalSnapshot`) verified independently by the backend.
5. **Security by Default**: Strict per-user isolation, SSRF/DNS-rebinding protections, prompt-injection sanitization, magic-byte file upload checks, Fernet encryption at rest for extracted resume text, and user data export/deletion.

## Extension Points for Future Releases

- **Chrome Browser Extension**: Reuses the FastAPI `/api/v1/applications`, `/api/v1/profile`, and `/api/v1/applications/{id}/approve` contracts with `Authorization: Bearer` tokens.
- **Team Hackathon Applications & Cover Letters**: Extend `ProfileContext` and `AIProvider` (`match_ambiguous_fields` / cover-letter generator method) without altering backend workflow orchestration.
- **Cloud / Self-Hosted Inference & Fine-Tuned Classifier**: Implement a new `AIProvider` subclass alongside `OllamaProvider`.
- **Subscription Billing & Multi-Language**: Extend the `Subscription` model (`plan_code`, `monthly_application_limit`) and `frontend` localization without schema breaking changes.

# Security Model, Deployment Readiness & Known Limitations

## Security Controls Implemented

1. **Authentication & Session Isolation**:
   - Passwords hashed using Argon2id (`argon2-cffi`) with timing-equalized unknown-email checks.
   - JWT access tokens (`HS256`) stored in `HttpOnly; SameSite=Lax` cookies (and accepted via `Authorization: Bearer` for API clients).
   - Double-submit `X-CSRF-Token` validation enforced on all cookie-authenticated unsafe mutations (`POST`, `PUT`, `PATCH`, `DELETE`).
   - Sliding-window IP rate limiting on `/api/v1/auth/register` and `/api/v1/auth/login`.
   - Strict `user_id` ownership scoping across profiles, resumes, applications, screenshots, and audit logs.
2. **URL & Browser Isolation**:
   - `validate_target_url` restricts destinations to `http://` and `https://`, blocks embedded credentials, private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local metadata (`169.254.169.254`), and loopback (`127.0.0.0/8`, `::1`) unless `ALLOW_LOCALHOST_AUTOMATION=true` for controlled local testing.
   - Anti-DNS-rebinding check rejects non-localhost hostnames resolving to private or loopback IPs even in test mode.
   - Playwright runs per-task isolated browser contexts (`accept_downloads=False`) with navigation route guards.
   - CAPTCHA/OTP/bot-protection prompts pause execution (`WAITING_FOR_USER_INPUT`) without attempting bypass.
3. **Prompt Injection & No-Fabrication Defenses**:
   - Webpage DOM labels and text are stripped of control characters, bounded in length, sanitized, and isolated inside `<untrusted_form_fields>` delimiters.
   - LLM output must validate strictly against Pydantic schemas and an `ALLOWED_PROFILE_KEYS` allowlist; local filesystem paths, tokens, cookies, and password hashes are never included in prompts.
4. **Immutable Approval Snapshots**:
   - Submissions are blocked (`409 Conflict`) unless `status == "APPROVED"` and an unconsumed `ApprovalSnapshot` matches the current `target_url`, `resume_sha256`, `form_structure_hash`, and `approved_values`.
   - Uncertain submission outcomes enter `UNKNOWN` and disallow automatic retries to prevent duplicate submissions.

## PostgreSQL & Multi-User SaaS Readiness

- Set `DATABASE_URL=postgresql+psycopg://user:password@host:5432/applypilot` (or `postgresql+psycopg2://...`) and run `alembic upgrade head` — all migrations (`20261110_0001`, `20261110_0002`) use portable SQLAlchemy column types and constraint naming conventions.
- Set `APP_ENV=production`, a strong >=32-character `SECRET_KEY`, `COOKIE_SECURE=true`, and `ALLOW_LOCALHOST_AUTOMATION=false`.
- `users.plan_tier` and `usage_events` capture per-user operational metering ready for future billing/quota enforcement.

## Current Known Limitations

- **Live Ollama Dependency**: Live AI field classification and open-ended drafting require Ollama running at `http://localhost:11434` with `qwen3:4b` (or `qwen3:1.7b`). When Ollama is absent, deterministic matching still runs and unknown/descriptive fields remain empty for manual entry.
- **External Websites**: Complex custom SPAs with shadow DOMs, authenticated portals requiring 2FA/SSO, or CAPTCHA-protected sites require manual intervention or assisted completion.
- **Rate Limiter Storage**: In-memory sliding-window rate limiter is designed for single-process local/MVP use; multi-worker cloud deployments should swap in Redis-backed rate limiting.


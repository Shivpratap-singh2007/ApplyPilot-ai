# Production Deployment & Multi-User SaaS Architecture

## Target Architecture

1. **Reverse Proxy (TLS Termination)**: Nginx / Caddy / Cloud Load Balancer routes `/` to Next.js (`frontend:3000`) and `/api/v1/*` to FastAPI (`backend:8000`).
2. **PostgreSQL Database**:
   - Switch `DATABASE_URL` to `postgresql+psycopg://user:pass@host:5432/applypilot`.
   - Run `alembic upgrade head` prior to rolling out application replicas.
3. **Stateless API Replicas + Worker Isolation**:
   - Authentication uses signed JWTs (`HttpOnly; Secure; SameSite=Lax`) and DB-backed records; replace the in-memory `SlidingWindowRateLimiter` with a Redis-backed limiter when running multiple API replicas.
   - Offload `run_draft_pipeline` and `submit_approved_application` from FastAPI `BackgroundTasks` onto a dedicated worker queue (e.g., Dramatiq/Celery + Playwright worker pool) so browser contexts stay isolated from API workers.
4. **Object Storage & Encryption**:
   - Store uploaded resumes and screenshots in encrypted object storage (S3/GCS/MinIO) keyed by `user_id` instead of local disk volumes.
5. **Local / Self-Hosted Inference**:
   - Keep `OLLAMA_BASE_URL` pointed at a private internal Ollama/vLLM host (`http://ollama-internal:11434`)—zero external paid LLM APIs required.
6. **Observability & Metering**:
   - Scrape `/api/v1/health` and `/api/v1/metrics` for uptime and lifecycle counts (`submitted`, `failed`, `unknown`), and enforce plan quotas via `subscriptions` and `usage_events`.


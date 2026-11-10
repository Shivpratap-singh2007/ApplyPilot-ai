# Troubleshooting Guide

## 1. Ollama Shows `unreachable` on Dashboard or Settings
- Verify Ollama is running: `ollama serve` or check http://127.0.0.1:11434/api/tags.
- Confirm the configured model is pulled: `ollama list`.
- If `qwen3:4b` is too heavy on RAM, pull `qwen3:1.7b` and set it in **Settings** (`preferred_ollama_model`) or `.env` (`OLLAMA_MODEL=qwen3:1.7b`).

## 2. `localhost` Target URL Blocked on New Application
- By design, `ALLOW_LOCALHOST_AUTOMATION=false` blocks localhost and private-network URLs to protect against SSRF.
- To test against the local forms server (`.\scripts\start-test-sites.ps1`), temporarily set `ALLOW_LOCALHOST_AUTOMATION=true` in `.env` and restart the backend.

## 3. Playwright Fails to Launch Browser
- Install Playwright's Chromium binary:
  ```powershell
  .\.venv\Scripts\python.exe -m playwright install chromium
  ```
- Otherwise `PlaywrightDraftWorker` falls back automatically to local Google Chrome (`chrome`) or Microsoft Edge (`msedge`).

## 4. Database Locked or Schema Out of Date
- Stop running `uvicorn` instances and run:
  ```powershell
  .\scripts\migrate.ps1
  ```

## 5. `UNKNOWN` Submission Status
- ApplyPilot AI intentionally never auto-retries `UNKNOWN` submissions to avoid duplicate applications. Check confirmation emails or target portal directly, or click **Cancel** if confirmed not submitted.


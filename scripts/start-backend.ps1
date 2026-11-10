$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $RepoRoot "backend")
try {
    & (Join-Path $RepoRoot ".venv\Scripts\python.exe") -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} finally {
    Pop-Location
}


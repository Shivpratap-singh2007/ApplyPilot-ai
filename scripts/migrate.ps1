$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $RepoRoot "backend")
try {
    & (Join-Path $RepoRoot ".venv\Scripts\python.exe") -m alembic upgrade head
} finally {
    Pop-Location
}


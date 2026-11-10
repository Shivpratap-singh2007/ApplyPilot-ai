$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path (Join-Path $RepoRoot ".env"))) {
    Copy-Item (Join-Path $RepoRoot ".env.example") (Join-Path $RepoRoot ".env")
    Write-Host "Created .env from .env.example"
}

if (-not (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe"))) {
    python -m venv (Join-Path $RepoRoot ".venv")
}

& (Join-Path $RepoRoot ".venv\Scripts\python.exe") -m pip install -r (Join-Path $RepoRoot "backend\requirements-dev.txt")
& (Join-Path $RepoRoot ".venv\Scripts\python.exe") -m pip install -r (Join-Path $RepoRoot "agent\requirements.txt")
& (Join-Path $RepoRoot "scripts\migrate.ps1")
npm --prefix (Join-Path $RepoRoot "frontend") install
npm --prefix (Join-Path $RepoRoot "frontend") run build

Write-Host "Setup complete. Run .\scripts\start-backend.ps1 and .\scripts\start-frontend.ps1 in separate terminals." -ForegroundColor Green


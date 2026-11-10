param(
    [string]$Model = "qwen3:4b",
    [string]$FallbackModel = "qwen3:1.7b"
)

$ErrorActionPreference = "Stop"

$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaExe = if ($ollamaCmd) { $ollamaCmd.Source } else { Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe" }
if (-not (Test-Path $ollamaExe)) {
    Write-Host "Ollama is not installed or not on PATH." -ForegroundColor Yellow
    Write-Host "Install from https://ollama.com/download (or 'winget install --id Ollama.Ollama -e'), then re-run this script."
    exit 1
}

try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2
    Write-Host "Local Ollama is already running at http://127.0.0.1:11434." -ForegroundColor Green
} catch {
    Write-Host "Starting Ollama daemon..."
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

Write-Host "Pulling local model $Model (or fallback $FallbackModel)..."
& $ollamaExe pull $Model
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falling back to smaller model $FallbackModel..." -ForegroundColor Yellow
    & $ollamaExe pull $FallbackModel
}

Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | ConvertTo-Json -Depth 3

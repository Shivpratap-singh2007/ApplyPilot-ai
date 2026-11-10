param(
    [Parameter(Mandatory = $true)]
    [string]$Url,
    [switch]$AllowLocalhost
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ArgsList = @("-m", "applypilot_agent.cli", $Url)
if ($AllowLocalhost) {
    $ArgsList += "--allow-localhost"
}

$env:PYTHONPATH = Join-Path $RepoRoot "agent"
& (Join-Path $RepoRoot ".venv\Scripts\python.exe") @ArgsList


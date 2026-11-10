param(
    [int]$Port = 8099
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Code = @"
import sys, time
sys.path.insert(0, r'$RepoRoot\tests')
from test_sites.internship_server import LocalInternshipServer
srv = LocalInternshipServer(host='127.0.0.1', port=$Port).start()
print(f'Local test forms server running at {srv.base_url}')
print('Routes: /internship, /job, /hackathon, /multistep, /upload, /dynamic, /missing-required, /validation-error, /captcha-form, /ambiguous-submit')
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    srv.stop()
"@

& (Join-Path $RepoRoot ".venv\Scripts\python.exe") -c $Code


param([int]$Port = 8769)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    Write-Host "IteraGuard v5.6 Arena: http://127.0.0.1:$Port"
    Write-Host 'Synthetic input only. Model identity is NOT attested. .env is not auto-loaded.'
    python -X utf8 -m arena.server --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Arena exited with code $LASTEXITCODE" }
} finally { Pop-Location }

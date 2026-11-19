$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
python tools/validate_v50.py --report-dir (Join-Path (Split-Path $PSScriptRoot -Parent) 'v50_validation') @args
if ($LASTEXITCODE -ne 0) { throw 'v5 validation failed. Read validation_summary.json and per-check logs.' }
Write-Output 'PASS implementation regressions. Independent evaluation and device execution remain separate evidence.'

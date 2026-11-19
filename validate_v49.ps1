$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
python -m unittest discover -s tests_v49 -v
if ($LASTEXITCODE -ne 0) { throw 'v4.9 tests failed' }
python -m unittest discover -s dmsg/tests -v
if ($LASTEXITCODE -ne 0) { throw 'Source regression failed' }
Write-Output 'PASS code tests only. Actual model and device validation are separate.'

param([Parameter(Mandatory=$true)][string]$PythonPath,[Parameter(Mandatory=$true)][string]$KevExport)
$ErrorActionPreference='Stop'
if (!(Test-Path -LiteralPath (Join-Path $KevExport 'head.pt'))) { throw 'A verified kev export with head.pt is required. Zoro generation weights are insufficient.' }
& $PythonPath -m kev.serve --run $KevExport --port 8008
if ($LASTEXITCODE -ne 0) { throw 'kev startup failed; do not enable LIVE mode.' }
